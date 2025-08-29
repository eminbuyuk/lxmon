import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { serversAPI, type Server, type Command } from '../services/api';
import { Plus, Terminal, Play } from 'lucide-react';

const Servers: React.FC = () => {
  const [selectedServer, setSelectedServer] = useState<Server | null>(null);
  const [command, setCommand] = useState('');
  const [showCommandForm, setShowCommandForm] = useState(false);

  const queryClient = useQueryClient();

  const { data: servers, isLoading } = useQuery({
    queryKey: ['servers'],
    queryFn: () => serversAPI.getServers(),
    refetchInterval: 30000,
  });

  const { data: commands } = useQuery({
    queryKey: ['server-commands', selectedServer?.id],
    queryFn: () => selectedServer ? serversAPI.getServerCommands(selectedServer.id) : null,
    enabled: !!selectedServer,
  });

  const sendCommandMutation = useMutation({
    mutationFn: ({ serverId, command }: { serverId: number; command: string }) =>
      serversAPI.sendCommand(serverId, command),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['server-commands', selectedServer?.id] });
      setCommand('');
      setShowCommandForm(false);
    },
  });

  const handleSendCommand = () => {
    if (selectedServer && command.trim()) {
      sendCommandMutation.mutate({ serverId: selectedServer.id, command: command.trim() });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Servers</h1>
          <p className="text-gray-600">Manage and monitor your servers</p>
        </div>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 flex items-center">
          <Plus className="h-4 w-4 mr-2" />
          Add Server
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Servers List */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Server List</h2>
          </div>
          <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
            {servers?.data.map((server: Server) => (
              <div
                key={server.id}
                className={`px-6 py-4 cursor-pointer hover:bg-gray-50 ${
                  selectedServer?.id === server.id ? 'bg-blue-50' : ''
                }`}
                onClick={() => setSelectedServer(server)}
              >
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
                    <p className="text-xs text-gray-400">{server.status}</p>
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

        {/* Server Details */}
        <div className="bg-white rounded-lg shadow">
          {selectedServer ? (
            <div>
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-medium text-gray-900">{selectedServer.name}</h2>
                  <button
                    onClick={() => setShowCommandForm(!showCommandForm)}
                    className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 flex items-center"
                  >
                    <Terminal className="h-4 w-4 mr-1" />
                    Send Command
                  </button>
                </div>
              </div>

              <div className="p-6 space-y-4">
                {/* Server Info */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-600">Hostname:</span>
                    <p className="text-gray-900">{selectedServer.hostname}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">IP Address:</span>
                    <p className="text-gray-900">{selectedServer.ip_address || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">Status:</span>
                    <p className={`font-medium ${
                      selectedServer.status === 'online' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {selectedServer.status}
                    </p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">Last Heartbeat:</span>
                    <p className="text-gray-900">
                      {selectedServer.last_heartbeat
                        ? new Date(selectedServer.last_heartbeat).toLocaleString()
                        : 'Never'
                      }
                    </p>
                  </div>
                </div>

                {/* Command Form */}
                {showCommandForm && (
                  <div className="border-t pt-4">
                    <div className="flex space-x-2">
                      <input
                        type="text"
                        value={command}
                        onChange={(e) => setCommand(e.target.value)}
                        placeholder="Enter command (e.g., systemctl status nginx)"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                        onKeyPress={(e) => e.key === 'Enter' && handleSendCommand()}
                      />
                      <button
                        onClick={handleSendCommand}
                        disabled={!command.trim() || sendCommandMutation.isPending}
                        className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center"
                      >
                        <Play className="h-4 w-4 mr-1" />
                        {sendCommandMutation.isPending ? 'Sending...' : 'Send'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Recent Commands */}
                <div className="border-t pt-4">
                  <h3 className="text-sm font-medium text-gray-900 mb-2">Recent Commands</h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {commands?.data.slice(0, 5).map((cmd: Command) => (
                      <div key={cmd.id} className="bg-gray-50 p-3 rounded text-sm">
                        <div className="flex items-center justify-between mb-1">
                          <code className="text-gray-800 font-mono">{cmd.command}</code>
                          <span className={`px-2 py-1 rounded text-xs ${
                            cmd.status === 'completed'
                              ? 'bg-green-100 text-green-800'
                              : cmd.status === 'failed'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {cmd.status}
                          </span>
                        </div>
                        {cmd.stdout && (
                          <pre className="text-xs text-gray-600 bg-white p-2 rounded mt-1 overflow-x-auto">
                            {cmd.stdout}
                          </pre>
                        )}
                        {cmd.stderr && (
                          <pre className="text-xs text-red-600 bg-white p-2 rounded mt-1 overflow-x-auto">
                            {cmd.stderr}
                          </pre>
                        )}
                      </div>
                    ))}
                    {(!commands?.data || commands.data.length === 0) && (
                      <p className="text-gray-500 text-sm">No commands executed yet</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-gray-500">
              Select a server to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Servers;
