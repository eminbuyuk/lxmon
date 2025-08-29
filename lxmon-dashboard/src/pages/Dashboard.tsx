import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { serversAPI, type Server } from '../services/api';
import { ServerIcon, AlertTriangle, CheckCircle } from 'lucide-react';

const Dashboard: React.FC = () => {
  const { data: servers, isLoading, error } = useQuery({
    queryKey: ['servers'],
    queryFn: () => serversAPI.getServers(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="text-red-800">Error loading servers: {error.message}</div>
      </div>
    );
  }

  const serverStats = {
    total: servers?.data.length || 0,
    online: servers?.data.filter((s: Server) => s.status === 'online').length || 0,
    offline: servers?.data.filter((s: Server) => s.status === 'offline').length || 0,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">System monitoring overview</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <ServerIcon className="h-8 w-8 text-blue-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Servers</p>
              <p className="text-2xl font-bold text-gray-900">{serverStats.total}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <CheckCircle className="h-8 w-8 text-green-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Online</p>
              <p className="text-2xl font-bold text-gray-900">{serverStats.online}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <AlertTriangle className="h-8 w-8 text-red-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Offline</p>
              <p className="text-2xl font-bold text-gray-900">{serverStats.offline}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Servers List */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Servers</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {servers?.data.map((server: Server) => (
            <div key={server.id} className="px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className={`w-3 h-3 rounded-full mr-3 ${
                    server.status === 'online' ? 'bg-green-400' : 'bg-red-400'
                  }`} />
                  <div>
                    <h3 className="text-sm font-medium text-gray-900">{server.name}</h3>
                    <p className="text-sm text-gray-500">{server.hostname}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500">{server.ip_address || 'N/A'}</p>
                  <p className="text-xs text-gray-400">
                    {server.last_heartbeat
                      ? `Last seen: ${new Date(server.last_heartbeat).toLocaleString()}`
                      : 'Never seen'
                    }
                  </p>
                </div>
              </div>
            </div>
          ))}
          {servers?.data.length === 0 && (
            <div className="px-6 py-8 text-center text-gray-500">
              No servers registered yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
