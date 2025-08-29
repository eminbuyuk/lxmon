import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { serversAPI, type Server } from '../services/api';
import {
  ServerIcon,
  AlertTriangle,
  CheckCircle,
  Activity,
  Cpu,
  HardDrive,
  Wifi,
  RefreshCw,
  Moon,
  Sun,
  TrendingUp,
  Clock
} from 'lucide-react';

const Dashboard: React.FC = () => {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const { data: servers, isLoading, error, refetch, isRefetching } = useQuery({
    queryKey: ['servers'],
    queryFn: () => serversAPI.getServers(),
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Update last update time when data changes
  useEffect(() => {
    if (servers) {
      setLastUpdate(new Date());
    }
  }, [servers]);

  // Toggle dark mode
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  // Manual refresh
  const handleRefresh = async () => {
    try {
      await refetch();
    } catch (error) {
      console.error('Refresh failed:', error);
    }
  };

  if (isLoading && !servers) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error && !servers) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div className="flex items-center">
          <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400 mr-3" />
          <div>
            <h3 className="text-lg font-medium text-red-800 dark:text-red-200">Connection Error</h3>
            <p className="text-red-700 dark:text-red-300 mt-1">
              Unable to load server data. Please check your connection and try again.
            </p>
            <button
              onClick={handleRefresh}
              className="mt-3 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const serverStats = {
    total: servers?.data?.length || 0,
    online: servers?.data?.filter((s: Server) => s.status === 'online').length || 0,
    offline: servers?.data?.filter((s: Server) => s.status === 'offline').length || 0,
  };

  const uptimePercentage = serverStats.total > 0
    ? Math.round((serverStats.online / serverStats.total) * 100)
    : 0;

  return (
    <div className="space-y-6 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            System monitoring overview
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
            <Clock className="h-4 w-4 mr-1" />
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
          <button
            onClick={handleRefresh}
            disabled={isRefetching}
            className="p-2 rounded-md bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors disabled:opacity-50"
            title="Refresh data"
          >
            <RefreshCw className={`h-5 w-5 ${isRefetching ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="p-2 rounded-md bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
          >
            {isDarkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 transition-colors">
          <div className="flex items-center">
            <ServerIcon className="h-8 w-8 text-blue-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Servers</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{serverStats.total}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 transition-colors">
          <div className="flex items-center">
            <CheckCircle className="h-8 w-8 text-green-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Online</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{serverStats.online}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 transition-colors">
          <div className="flex items-center">
            <AlertTriangle className="h-8 w-8 text-red-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Offline</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{serverStats.offline}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 transition-colors">
          <div className="flex items-center">
            <TrendingUp className="h-8 w-8 text-purple-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Uptime</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{uptimePercentage}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* System Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 transition-colors">
          <div className="flex items-center">
            <Cpu className="h-6 w-6 text-blue-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg CPU</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">--%</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 transition-colors">
          <div className="flex items-center">
            <Activity className="h-6 w-6 text-green-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Memory</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">--%</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 transition-colors">
          <div className="flex items-center">
            <HardDrive className="h-6 w-6 text-yellow-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Disk</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">--%</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 transition-colors">
          <div className="flex items-center">
            <Wifi className="h-6 w-6 text-purple-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Network I/O</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">-- MB/s</p>
            </div>
          </div>
        </div>
      </div>

      {/* Servers List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow transition-colors">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">Servers</h2>
            <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
              <div className="flex items-center">
                <div className="w-2 h-2 bg-green-400 rounded-full mr-1"></div>
                Online
              </div>
              <div className="flex items-center">
                <div className="w-2 h-2 bg-red-400 rounded-full mr-1"></div>
                Offline
              </div>
            </div>
          </div>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {servers?.data?.map((server: Server) => (
            <div key={server.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className={`w-3 h-3 rounded-full mr-3 ${
                    server.status === 'online' ? 'bg-green-400' : 'bg-red-400'
                  }`} />
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white">{server.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{server.hostname}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500 dark:text-gray-400">{server.ip_address || 'N/A'}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    {server.last_heartbeat
                      ? `Last seen: ${new Date(server.last_heartbeat).toLocaleString()}`
                      : 'Never seen'
                    }
                  </p>
                </div>
              </div>
            </div>
          ))}
          {servers?.data?.length === 0 && (
            <div className="px-6 py-12 text-center">
              <ServerIcon className="h-12 w-12 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No servers registered</h3>
              <p className="text-gray-500 dark:text-gray-400">
                Get started by registering your first server with the lxmon agent.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Error State Banner */}
      {error && servers && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 mr-3" />
            <div className="flex-1">
              <p className="text-yellow-800 dark:text-yellow-200">
                Some data may be outdated. Last successful update: {lastUpdate.toLocaleString()}
              </p>
            </div>
            <button
              onClick={handleRefresh}
              className="ml-4 px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700 transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
