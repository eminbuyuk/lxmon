package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/load"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/shirou/gopsutil/v3/process"
	gopsutilnet "github.com/shirou/gopsutil/v3/net"
)

// Configuration
type Config struct {
	ServerURL     string        `json:"server_url"`
	APIKey        string        `json:"api_key"`
	Interval      time.Duration `json:"interval"`
	Hostname      string        `json:"hostname"`
	MaxTimeout    time.Duration `json:"max_timeout"`
	MaxRetries    int           `json:"max_retries"`
	RetryDelay    time.Duration `json:"retry_delay"`
	LogLevel      string        `json:"log_level"`
	EnableDebug   bool          `json:"enable_debug"`
}

// Metric data structure
type Metric struct {
	MetricType  string                 `json:"metric_type"`
	MetricName  string                 `json:"metric_name"`
	Value       float64                `json:"value"`
	Unit        string                 `json:"unit,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
	Timestamp   time.Time              `json:"timestamp"`
}

// Metrics payload
type MetricsPayload struct {
	Hostname string   `json:"hostname"`
	Metrics  []Metric `json:"metrics"`
	APIKey   string   `json:"api_key"`
}

// Command result
type CommandResult struct {
	CommandID int       `json:"command_id"`
	ExitCode  int       `json:"exit_code"`
	Stdout    string    `json:"stdout"`
	Stderr    string    `json:"stderr"`
	Duration  float64   `json:"duration_seconds"`
	Timestamp time.Time `json:"timestamp"`
}

// Pending command
type PendingCommand struct {
	ID      int    `json:"id"`
	Command string `json:"command"`
}

var (
	config     Config
	shutdownCh = make(chan os.Signal, 1)
	wg         sync.WaitGroup
)

func init() {
	// Load configuration
	loadConfig()

	// Setup signal handling for graceful shutdown
	signal.Notify(shutdownCh, syscall.SIGINT, syscall.SIGTERM)
}

func loadConfig() {
	// Default configuration
	config = Config{
		ServerURL:  "http://localhost:8000",
		APIKey:     "agent-key-1",
		Interval:   60 * time.Second,
		MaxTimeout: 300 * time.Second,
		MaxRetries: 3,
		RetryDelay: 5 * time.Second,
		LogLevel:   "info",
		EnableDebug: false,
	}

	// Override from environment variables
	if value := os.Getenv("LXMON_SERVER_URL"); value != "" {
		config.ServerURL = value
	}
	if value := os.Getenv("LXMON_API_KEY"); value != "" {
		config.APIKey = value
	}
	if value := os.Getenv("LXMON_INTERVAL"); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			config.Interval = time.Duration(intValue) * time.Second
		}
	}
	if value := os.Getenv("LXMON_MAX_TIMEOUT"); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			config.MaxTimeout = time.Duration(intValue) * time.Second
		}
	}
	if value := os.Getenv("LXMON_MAX_RETRIES"); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			config.MaxRetries = intValue
		}
	}
	if value := os.Getenv("LXMON_DEBUG"); value == "true" {
		config.EnableDebug = true
	}

	// Get hostname
	hostname, err := os.Hostname()
	if err != nil {
		log.Fatalf("Failed to get hostname: %v", err)
	}
	config.Hostname = hostname
}

func main() {
	log.Printf("🚀 Starting lxmon-agent on %s", config.Hostname)
	log.Printf("📡 Server URL: %s", config.ServerURL)
	log.Printf("⏱️  Collection interval: %v", config.Interval)
	if config.EnableDebug {
		log.Printf("🐛 Debug mode enabled")
	}

	// Register agent with retry
	if err := registerAgentWithRetry(); err != nil {
		log.Fatalf("❌ Failed to register agent after retries: %v", err)
	}

	// Start metrics collection
	ticker := time.NewTicker(config.Interval)
	defer ticker.Stop()

	// Initial collection
	wg.Add(1)
	go func() {
		defer wg.Done()
		collectAndSendMetrics()
	}()

	// Main loop
	for {
		select {
		case <-ticker.C:
			wg.Add(1)
			go func() {
				defer wg.Done()
				collectAndSendMetrics()
				checkAndExecuteCommands()
			}()
		case <-shutdownCh:
			log.Println("🛑 Received shutdown signal, stopping agent...")
			ticker.Stop()
			wg.Wait()
			log.Println("✅ Agent shutdown complete")
			return
		}
	}
}

func registerAgentWithRetry() error {
	var lastErr error
	for attempt := 1; attempt <= config.MaxRetries; attempt++ {
		if err := registerAgent(); err != nil {
			lastErr = err
			log.Printf("⚠️  Registration attempt %d failed: %v", attempt, err)
			if attempt < config.MaxRetries {
				time.Sleep(config.RetryDelay)
			}
		} else {
			return nil
		}
	}
	return lastErr
}

func registerAgent() error {
	payload := map[string]interface{}{
		"hostname":   config.Hostname,
		"ip_address": getLocalIP(),
		"api_key":    config.APIKey,
		"os_info":    getOSInfo(),
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal registration data: %w", err)
	}

	resp, err := http.Post(
		config.ServerURL+"/api/agent/register",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return fmt.Errorf("registration request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("registration failed with status %d: %s", resp.StatusCode, string(body))
	}

	log.Println("✅ Agent registered successfully")
	return nil
}

func collectAndSendMetrics() {
	startTime := time.Now()
	metrics := []Metric{}

	// CPU metrics
	if cpuPercent, err := cpu.Percent(time.Second, false); err == nil && len(cpuPercent) > 0 {
		metrics = append(metrics, Metric{
			MetricType: "cpu",
			MetricName: "usage_percent",
			Value:      cpuPercent[0],
			Unit:       "percent",
			Timestamp:  time.Now(),
		})
	}

	// CPU count
	if cpuCount, err := cpu.Counts(true); err == nil {
		metrics = append(metrics, Metric{
			MetricType: "cpu",
			MetricName: "count",
			Value:      float64(cpuCount),
			Unit:       "cores",
			Timestamp:  time.Now(),
		})
	}

	// Memory metrics
	if memInfo, err := mem.VirtualMemory(); err == nil {
		metrics = append(metrics, Metric{
			MetricType: "memory",
			MetricName: "total",
			Value:      float64(memInfo.Total),
			Unit:       "bytes",
			Timestamp:  time.Now(),
		})
		metrics = append(metrics, Metric{
			MetricType: "memory",
			MetricName: "used",
			Value:      float64(memInfo.Used),
			Unit:       "bytes",
			Timestamp:  time.Now(),
		})
		metrics = append(metrics, Metric{
			MetricType: "memory",
			MetricName: "used_percent",
			Value:      memInfo.UsedPercent,
			Unit:       "percent",
			Timestamp:  time.Now(),
		})
		metrics = append(metrics, Metric{
			MetricType: "memory",
			MetricName: "available",
			Value:      float64(memInfo.Available),
			Unit:       "bytes",
			Timestamp:  time.Now(),
		})
	}

	// Swap memory
	if swapInfo, err := mem.SwapMemory(); err == nil {
		metrics = append(metrics, Metric{
			MetricType: "memory",
			MetricName: "swap_total",
			Value:      float64(swapInfo.Total),
			Unit:       "bytes",
			Timestamp:  time.Now(),
		})
		metrics = append(metrics, Metric{
			MetricType: "memory",
			MetricName: "swap_used",
			Value:      float64(swapInfo.Used),
			Unit:       "bytes",
			Timestamp:  time.Now(),
		})
		metrics = append(metrics, Metric{
			MetricType: "memory",
			MetricName: "swap_used_percent",
			Value:      swapInfo.UsedPercent,
			Unit:       "percent",
			Timestamp:  time.Now(),
		})
	}

	// Disk metrics
	if partitions, err := disk.Partitions(false); err == nil {
		for _, partition := range partitions {
			if usage, err := disk.Usage(partition.Mountpoint); err == nil {
				metrics = append(metrics, Metric{
					MetricType: "disk",
					MetricName: "usage_percent",
					Value:      usage.UsedPercent,
					Unit:       "percent",
					Metadata: map[string]interface{}{
						"mountpoint": partition.Mountpoint,
						"filesystem": partition.Fstype,
						"device":     partition.Device,
					},
					Timestamp: time.Now(),
				})
				metrics = append(metrics, Metric{
					MetricType: "disk",
					MetricName: "total",
					Value:      float64(usage.Total),
					Unit:       "bytes",
					Metadata: map[string]interface{}{
						"mountpoint": partition.Mountpoint,
					},
					Timestamp: time.Now(),
				})
				metrics = append(metrics, Metric{
					MetricType: "disk",
					MetricName: "free",
					Value:      float64(usage.Free),
					Unit:       "bytes",
					Metadata: map[string]interface{}{
						"mountpoint": partition.Mountpoint,
					},
					Timestamp: time.Now(),
				})
			}
		}
	}

	// Network metrics
	if netStats, err := gopsutilnet.IOCounters(false); err == nil && len(netStats) > 0 {
		stats := netStats[0]
		metrics = append(metrics, Metric{
			MetricType: "network",
			MetricName: "bytes_sent",
			Value:      float64(stats.BytesSent),
			Unit:       "bytes",
			Timestamp:  time.Now(),
		})
		metrics = append(metrics, Metric{
			MetricType: "network",
			MetricName: "bytes_recv",
			Value:      float64(stats.BytesRecv),
			Unit:       "bytes",
			Timestamp:  time.Now(),
		})
		metrics = append(metrics, Metric{
			MetricType: "network",
			MetricName: "packets_sent",
			Value:      float64(stats.PacketsSent),
			Unit:       "packets",
			Timestamp:  time.Now(),
		})
		metrics = append(metrics, Metric{
			MetricType: "network",
			MetricName: "packets_recv",
			Value:      float64(stats.PacketsRecv),
			Unit:       "packets",
			Timestamp:  time.Now(),
		})
	}

	// Host info and load averages
	if hostInfo, err := host.Info(); err == nil {
		metrics = append(metrics, Metric{
			MetricType: "system",
			MetricName: "uptime",
			Value:      float64(hostInfo.Uptime),
			Unit:       "seconds",
			Timestamp:  time.Now(),
		})
	}

	// Load averages
	if loadAvg, err := load.Avg(); err == nil {
		metrics = append(metrics, Metric{
			MetricType: "system",
			MetricName: "load_average_1m",
			Value:      loadAvg.Load1,
			Unit:       "load",
			Timestamp:  time.Now(),
		})
		metrics = append(metrics, Metric{
			MetricType: "system",
			MetricName: "load_average_5m",
			Value:      loadAvg.Load5,
			Unit:       "load",
			Timestamp:  time.Now(),
		})
		metrics = append(metrics, Metric{
			MetricType: "system",
			MetricName: "load_average_15m",
			Value:      loadAvg.Load15,
			Unit:       "load",
			Timestamp:  time.Now(),
		})
	}

	// Process count
	if processes, err := process.Pids(); err == nil {
		metrics = append(metrics, Metric{
			MetricType: "system",
			MetricName: "process_count",
			Value:      float64(len(processes)),
			Unit:       "count",
			Timestamp:  time.Now(),
		})
	}

	// Collection duration
	collectionDuration := time.Since(startTime).Seconds()
	metrics = append(metrics, Metric{
		MetricType: "agent",
		MetricName: "collection_duration",
		Value:      collectionDuration,
		Unit:       "seconds",
		Timestamp:  time.Now(),
	})

	// Send metrics with retry
	payload := MetricsPayload{
		Hostname: config.Hostname,
		Metrics:  metrics,
		APIKey:   config.APIKey,
	}

	if err := sendMetricsWithRetry(payload); err != nil {
		log.Printf("❌ Failed to send metrics: %v", err)
	} else {
		log.Printf("✅ Sent %d metrics in %.2fs", len(metrics), collectionDuration)
	}
}

func sendMetricsWithRetry(payload MetricsPayload) error {
	var lastErr error
	for attempt := 1; attempt <= config.MaxRetries; attempt++ {
		if err := sendMetrics(payload); err != nil {
			lastErr = err
			if config.EnableDebug {
				log.Printf("⚠️  Metrics send attempt %d failed: %v", attempt, err)
			}
			if attempt < config.MaxRetries {
				time.Sleep(config.RetryDelay)
			}
		} else {
			return nil
		}
	}
	return lastErr
}

func sendMetrics(payload MetricsPayload) error {
	jsonData, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal metrics: %w", err)
	}

	req, err := http.NewRequest("POST", config.ServerURL+"/api/agent/metrics", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("metrics request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("metrics submission failed with status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

func checkAndExecuteCommands() {
	// Get pending commands
	req, err := http.NewRequest("GET", config.ServerURL+"/api/agent/commands", nil)
	if err != nil {
		log.Printf("❌ Failed to create commands request: %v", err)
		return
	}
	req.Header.Set("X-API-Key", config.APIKey)
	req.URL.RawQuery = fmt.Sprintf("hostname=%s", config.Hostname)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("❌ Failed to get commands: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("⚠️  Commands request failed with status %d", resp.StatusCode)
		return
	}

	var commands []PendingCommand
	if err := json.NewDecoder(resp.Body).Decode(&commands); err != nil {
		log.Printf("❌ Failed to decode commands: %v", err)
		return
	}

	if len(commands) > 0 {
		log.Printf("📋 Found %d pending commands", len(commands))
	}

	// Execute commands concurrently
	for _, cmd := range commands {
		wg.Add(1)
		go func(command PendingCommand) {
			defer wg.Done()
			executeCommand(command)
		}(cmd)
	}
}

func executeCommand(cmd PendingCommand) {
	startTime := time.Now()
	log.Printf("⚙️  Executing command %d: %s", cmd.ID, cmd.Command)

	// Create context with timeout
	ctx, cancel := context.WithTimeout(context.Background(), config.MaxTimeout)
	defer cancel()

	// Execute command
	execCmd := exec.CommandContext(ctx, "bash", "-c", cmd.Command)
	var stdout, stderr bytes.Buffer
	execCmd.Stdout = &stdout
	execCmd.Stderr = &stderr

	err := execCmd.Run()
	duration := time.Since(startTime).Seconds()
	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = 1
		}
	}

	// Send result with retry
	result := CommandResult{
		CommandID: cmd.ID,
		ExitCode:  exitCode,
		Stdout:    stdout.String(),
		Stderr:    stderr.String(),
		Duration:  duration,
		Timestamp: time.Now(),
	}

	if err := sendCommandResultWithRetry(result); err != nil {
		log.Printf("❌ Failed to send command result: %v", err)
	} else {
		log.Printf("✅ Command %d completed with exit code %d in %.2fs", cmd.ID, exitCode, duration)
	}
}

func sendCommandResultWithRetry(result CommandResult) error {
	var lastErr error
	for attempt := 1; attempt <= config.MaxRetries; attempt++ {
		if err := sendCommandResult(result); err != nil {
			lastErr = err
			if config.EnableDebug {
				log.Printf("⚠️  Result send attempt %d failed: %v", attempt, err)
			}
			if attempt < config.MaxRetries {
				time.Sleep(config.RetryDelay)
			}
		} else {
			return nil
		}
	}
	return lastErr
}

func sendCommandResult(result CommandResult) error {
	jsonData, err := json.Marshal(result)
	if err != nil {
		return fmt.Errorf("failed to marshal result: %w", err)
	}

	req, err := http.NewRequest("POST", config.ServerURL+"/api/agent/command-result", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create result request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-API-Key", config.APIKey)
	req.URL.RawQuery = fmt.Sprintf("hostname=%s", config.Hostname)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("result request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("result submission failed with status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvAsInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func getLocalIP() string {
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		return "127.0.0.1"
	}
	defer conn.Close()

	localAddr := conn.LocalAddr().String()
	if idx := strings.LastIndex(localAddr, ":"); idx != -1 {
		return localAddr[:idx]
	}
	return localAddr
}

func getOSInfo() map[string]interface{} {
	hostInfo, err := host.Info()
	if err != nil {
		return map[string]interface{}{"error": "failed to get host info"}
	}

	return map[string]interface{}{
		"os":              hostInfo.OS,
		"platform":        hostInfo.Platform,
		"platform_family": hostInfo.PlatformFamily,
		"platform_version": hostInfo.PlatformVersion,
		"kernel_version":  hostInfo.KernelVersion,
		"kernel_arch":     hostInfo.KernelArch,
	}
}
