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
	"strconv"
	"strings"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	gopsutilnet "github.com/shirou/gopsutil/v3/net"
)

// Configuration
type Config struct {
	ServerURL   string
	APIKey      string
	Interval    time.Duration
	Hostname    string
	MaxTimeout  time.Duration
}

// Metric data structure
type Metric struct {
	MetricType  string                 `json:"metric_type"`
	MetricName  string                 `json:"metric_name"`
	Value       float64                `json:"value"`
	Unit        string                 `json:"unit,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// Metrics payload
type MetricsPayload struct {
	Hostname string   `json:"hostname"`
	Metrics  []Metric `json:"metrics"`
	APIKey   string   `json:"api_key"`
}

// Command result
type CommandResult struct {
	CommandID int    `json:"command_id"`
	ExitCode  int    `json:"exit_code"`
	Stdout    string `json:"stdout"`
	Stderr    string `json:"stderr"`
}

// Pending command
type PendingCommand struct {
	ID      int    `json:"id"`
	Command string `json:"command"`
}

var config Config

func init() {
	// Load configuration from environment variables
	config.ServerURL = getEnv("LXMON_SERVER_URL", "http://localhost:8000")
	config.APIKey = getEnv("LXMON_API_KEY", "agent-key-1")
	config.Interval = time.Duration(getEnvAsInt("LXMON_INTERVAL", 60)) * time.Second
	config.MaxTimeout = time.Duration(getEnvAsInt("LXMON_MAX_TIMEOUT", 300)) * time.Second

	// Get hostname
	hostname, err := os.Hostname()
	if err != nil {
		log.Fatalf("Failed to get hostname: %v", err)
	}
	config.Hostname = hostname
}

func main() {
	log.Printf("Starting lxmon-agent on %s", config.Hostname)
	log.Printf("Server URL: %s", config.ServerURL)
	log.Printf("Collection interval: %v", config.Interval)

	// Register agent
	if err := registerAgent(); err != nil {
		log.Fatalf("Failed to register agent: %v", err)
	}

	// Start metrics collection
	ticker := time.NewTicker(config.Interval)
	defer ticker.Stop()

	// Initial collection
	collectAndSendMetrics()

	for {
		select {
		case <-ticker.C:
			collectAndSendMetrics()
			checkAndExecuteCommands()
		}
	}
}

func registerAgent() error {
	payload := map[string]interface{}{
		"hostname":   config.Hostname,
		"ip_address": getLocalIP(),
		"api_key":    config.APIKey,
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

	log.Println("Agent registered successfully")
	return nil
}

func collectAndSendMetrics() {
	metrics := []Metric{}

	// CPU metrics
	if cpuPercent, err := cpu.Percent(time.Second, false); err == nil && len(cpuPercent) > 0 {
		metrics = append(metrics, Metric{
			MetricType: "cpu",
			MetricName: "usage_percent",
			Value:      cpuPercent[0],
			Unit:       "percent",
		})
	}

	// Memory metrics
	if memInfo, err := mem.VirtualMemory(); err == nil {
		metrics = append(metrics, Metric{
			MetricType: "memory",
			MetricName: "total",
			Value:      float64(memInfo.Total),
			Unit:       "bytes",
		})
		metrics = append(metrics, Metric{
			MetricType: "memory",
			MetricName: "used",
			Value:      float64(memInfo.Used),
			Unit:       "bytes",
		})
		metrics = append(metrics, Metric{
			MetricType: "memory",
			MetricName: "used_percent",
			Value:      memInfo.UsedPercent,
			Unit:       "percent",
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
					},
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
		})
		metrics = append(metrics, Metric{
			MetricType: "network",
			MetricName: "bytes_recv",
			Value:      float64(stats.BytesRecv),
			Unit:       "bytes",
		})
	}

	// Host info
	if hostInfo, err := host.Info(); err == nil {
		metrics = append(metrics, Metric{
			MetricType: "system",
			MetricName: "uptime",
			Value:      float64(hostInfo.Uptime),
			Unit:       "seconds",
		})
	}

	// Send metrics
	payload := MetricsPayload{
		Hostname: config.Hostname,
		Metrics:  metrics,
		APIKey:   config.APIKey,
	}

	if err := sendMetrics(payload); err != nil {
		log.Printf("Failed to send metrics: %v", err)
	} else {
		log.Printf("Sent %d metrics", len(metrics))
	}
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
		log.Printf("Failed to create commands request: %v", err)
		return
	}
	req.Header.Set("X-API-Key", config.APIKey)
	req.URL.RawQuery = fmt.Sprintf("hostname=%s", config.Hostname)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Failed to get commands: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Commands request failed with status %d", resp.StatusCode)
		return
	}

	var commands []PendingCommand
	if err := json.NewDecoder(resp.Body).Decode(&commands); err != nil {
		log.Printf("Failed to decode commands: %v", err)
		return
	}

	// Execute commands
	for _, cmd := range commands {
		go executeCommand(cmd)
	}
}

func executeCommand(cmd PendingCommand) {
	log.Printf("Executing command %d: %s", cmd.ID, cmd.Command)

	// Create context with timeout
	ctx, cancel := context.WithTimeout(context.Background(), config.MaxTimeout)
	defer cancel()

	// Execute command
	execCmd := exec.CommandContext(ctx, "bash", "-c", cmd.Command)
	var stdout, stderr bytes.Buffer
	execCmd.Stdout = &stdout
	execCmd.Stderr = &stderr

	err := execCmd.Run()
	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = 1
		}
	}

	// Send result
	result := CommandResult{
		CommandID: cmd.ID,
		ExitCode:  exitCode,
		Stdout:    stdout.String(),
		Stderr:    stderr.String(),
	}

	if err := sendCommandResult(result); err != nil {
		log.Printf("Failed to send command result: %v", err)
	} else {
		log.Printf("Command %d completed with exit code %d", cmd.ID, exitCode)
	}
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
