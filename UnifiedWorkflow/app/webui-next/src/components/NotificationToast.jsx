import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Info, 
  Loader2, 
  X,
  WifiOff,
  Wifi
} from 'lucide-react';
import { notifications } from '../utils/notificationSystem';

const NotificationToast = React.memo(() => {
  const [notificationList, setNotificationList] = useState([]);

  useEffect(() => {
    const unsubscribe = notifications.addListener(setNotificationList);
    return unsubscribe;
  }, []);

  const getNotificationIcon = useCallback((type) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-400" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-400" />;
      case 'info':
        return <Info className="w-5 h-5 text-blue-400" />;
      case 'loading':
        return <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />;
      case 'offline':
        return <WifiOff className="w-5 h-5 text-orange-400" />;
      default:
        return <Info className="w-5 h-5 text-gray-400" />;
    }
  }, []);

  const getNotificationStyles = useCallback((type) => {
    const baseClasses = "border backdrop-blur-lg";
    
    switch (type) {
      case 'success':
        return `${baseClasses} bg-green-900/20 border-green-600/50 text-green-100`;
      case 'error':
        return `${baseClasses} bg-red-900/20 border-red-600/50 text-red-100`;
      case 'warning':
        return `${baseClasses} bg-yellow-900/20 border-yellow-600/50 text-yellow-100`;
      case 'info':
        return `${baseClasses} bg-blue-900/20 border-blue-600/50 text-blue-100`;
      case 'loading':
        return `${baseClasses} bg-purple-900/20 border-purple-600/50 text-purple-100`;
      case 'offline':
        return `${baseClasses} bg-orange-900/20 border-orange-600/50 text-orange-100`;
      default:
        return `${baseClasses} bg-gray-900/20 border-gray-600/50 text-gray-100`;
    }
  }, []);

  const handleDismiss = useCallback((id) => {
    notifications.dismiss(id);
  }, []);

  const handleActionClick = useCallback((action, notificationId) => {
    if (action && action.callback) {
      action.callback();
    }
    // Auto-dismiss after action unless specified otherwise
    if (!action.keepOpen) {
      notifications.dismiss(notificationId);
    }
  }, []);

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm w-full">
      <AnimatePresence mode="popLayout">
        {notificationList.map((notification, index) => (
          <motion.div
            key={notification.id}
            initial={{ opacity: 0, x: 100, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.95 }}
            transition={{ 
              type: "spring",
              stiffness: 400,
              damping: 30,
              delay: index * 0.05
            }}
            className={`p-4 rounded-lg shadow-lg ${getNotificationStyles(notification.type)}`}
            layout
          >
            <div className="flex items-start space-x-3">
              {/* Icon */}
              <div className="flex-shrink-0 mt-0.5">
                {getNotificationIcon(notification.type)}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                {notification.title && (
                  <h4 className="font-semibold text-sm mb-1 truncate">
                    {notification.title}
                  </h4>
                )}
                <p className="text-sm leading-5 break-words">
                  {notification.message}
                </p>

                {/* Action Button */}
                {notification.action && (
                  <button
                    onClick={() => handleActionClick(notification.action, notification.id)}
                    className="mt-2 px-3 py-1 text-xs bg-white/10 hover:bg-white/20 rounded border border-white/20 transition-colors"
                  >
                    {notification.action.label}
                  </button>
                )}

                {/* Progress Bar for Loading */}
                {notification.type === 'loading' && notification.progress !== undefined && (
                  <div className="mt-2 w-full bg-gray-700 rounded-full h-1.5">
                    <motion.div
                      className="bg-purple-400 h-1.5 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${notification.progress}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                )}
              </div>

              {/* Dismiss Button */}
              {!notification.persistent && (
                <button
                  onClick={() => handleDismiss(notification.id)}
                  className="flex-shrink-0 p-1 hover:bg-white/10 rounded transition-colors"
                  aria-label="Dismiss notification"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Auto-dismiss Progress Bar */}
            {!notification.persistent && notification.duration > 0 && (
              <motion.div
                className="absolute bottom-0 left-0 h-0.5 bg-white/30 rounded-b-lg"
                initial={{ width: "100%" }}
                animate={{ width: "0%" }}
                transition={{ 
                  duration: notification.duration / 1000,
                  ease: "linear"
                }}
              />
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
});

NotificationToast.displayName = 'NotificationToast';

export default NotificationToast;