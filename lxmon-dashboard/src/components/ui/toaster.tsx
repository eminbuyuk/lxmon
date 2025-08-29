import React, { useState } from 'react';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface ToasterProps {
  toasts?: Toast[];
}

export const Toaster: React.FC<ToasterProps> = ({ toasts = [] }) => {
  const [localToasts, setLocalToasts] = useState<Toast[]>([]);

  const allToasts = [...toasts, ...localToasts];

  const removeToast = (id: string) => {
    setLocalToasts(prev => prev.filter(toast => toast.id !== id));
  };

  const addToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now().toString();
    const toast: Toast = { id, message, type };
    setLocalToasts(prev => [...prev, toast]);

    // Auto remove after 5 seconds
    setTimeout(() => removeToast(id), 5000);
  };

  // Expose addToast function globally for easy access
  React.useEffect(() => {
    (window as any).addToast = addToast;
  }, []);

  if (allToasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {allToasts.map((toast) => (
        <div
          key={toast.id}
          className={`p-4 rounded-lg shadow-lg max-w-sm ${
            toast.type === 'success'
              ? 'bg-green-500 text-white'
              : toast.type === 'error'
              ? 'bg-red-500 text-white'
              : 'bg-blue-500 text-white'
          }`}
        >
          <div className="flex items-center justify-between">
            <span>{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              className="ml-4 text-white hover:text-gray-200"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
