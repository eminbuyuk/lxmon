import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { alertsAPI, type Alert, type AlertRule } from '../services/api';
import { AlertTriangle, CheckCircle, Clock, Settings } from 'lucide-react';

const Alerts: React.FC = () => {
  const { data: alerts, isLoading: alertsLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => alertsAPI.getAlerts(),
    refetchInterval: 30000,
  });

  const { data: alertRules, isLoading: rulesLoading } = useQuery({
    queryKey: ['alert-rules'],
    queryFn: () => alertsAPI.getAlertRules(),
  });

  if (alertsLoading || rulesLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  const activeAlerts = alerts?.data.filter((alert: Alert) => alert.status === 'active') || [];
  const resolvedAlerts = alerts?.data.filter((alert: Alert) => alert.status === 'resolved') || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
        <p className="text-gray-600">Monitor system alerts and manage alert rules</p>
      </div>

      {/* Alert Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <AlertTriangle className="h-8 w-8 text-red-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Active Alerts</p>
              <p className="text-2xl font-bold text-gray-900">{activeAlerts.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <CheckCircle className="h-8 w-8 text-green-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Resolved</p>
              <p className="text-2xl font-bold text-gray-900">{resolvedAlerts.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <Settings className="h-8 w-8 text-blue-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Alert Rules</p>
              <p className="text-2xl font-bold text-gray-900">{alertRules?.data.length || 0}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Alerts */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Active Alerts</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {activeAlerts.map((alert: Alert) => (
              <div key={alert.id} className="px-6 py-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center">
                      <AlertTriangle className={`h-5 w-5 mr-2 ${
                        alert.severity === 'critical' ? 'text-red-500' :
                        alert.severity === 'error' ? 'text-orange-500' :
                        alert.severity === 'warning' ? 'text-yellow-500' :
                        'text-blue-500'
                      }`} />
                      <h3 className="text-sm font-medium text-gray-900">{alert.message}</h3>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      Triggered: {new Date(alert.triggered_at).toLocaleString()}
                    </p>
                  </div>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    alert.severity === 'critical' ? 'bg-red-100 text-red-800' :
                    alert.severity === 'error' ? 'bg-orange-100 text-orange-800' :
                    alert.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {alert.severity}
                  </span>
                </div>
              </div>
            ))}
            {activeAlerts.length === 0 && (
              <div className="px-6 py-8 text-center text-gray-500">
                No active alerts
              </div>
            )}
          </div>
        </div>

        {/* Alert Rules */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Alert Rules</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {alertRules?.data.map((rule: AlertRule) => (
              <div key={rule.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900">{rule.name}</h3>
                    <p className="text-sm text-gray-500">{rule.description}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {rule.metric_type}.{rule.metric_name} {rule.condition} {rule.threshold}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      rule.severity === 'critical' ? 'bg-red-100 text-red-800' :
                      rule.severity === 'error' ? 'bg-orange-100 text-orange-800' :
                      rule.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {rule.severity}
                    </span>
                    <div className={`w-2 h-2 rounded-full ${
                      rule.enabled ? 'bg-green-400' : 'bg-gray-400'
                    }`} />
                  </div>
                </div>
              </div>
            ))}
            {(!alertRules?.data || alertRules.data.length === 0) && (
              <div className="px-6 py-8 text-center text-gray-500">
                No alert rules configured
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Resolved Alerts */}
      {resolvedAlerts.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Recently Resolved</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {resolvedAlerts.slice(0, 5).map((alert: Alert) => (
              <div key={alert.id} className="px-6 py-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center">
                      <CheckCircle className="h-5 w-5 mr-2 text-green-500" />
                      <h3 className="text-sm font-medium text-gray-900">{alert.message}</h3>
                    </div>
                    <div className="flex items-center text-sm text-gray-500 mt-1">
                      <Clock className="h-4 w-4 mr-1" />
                      Resolved: {alert.resolved_at ? new Date(alert.resolved_at).toLocaleString() : 'Unknown'}
                    </div>
                  </div>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    resolved
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Alerts;
