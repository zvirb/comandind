import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  User,
  Bell,
  Shield,
  Palette,
  Globe,
  Database,
  Key,
  Moon,
  Sun,
  ArrowLeft,
  Save,
  ChevronRight,
  Mail,
  Smartphone,
  Monitor,
  Wifi,
  Lock
} from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';
import GoogleOAuthIntegration from '../components/GoogleOAuthIntegration';

const Settings = () => {
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState('profile');
  const [darkMode, setDarkMode] = useState(true);
  const [notifications, setNotifications] = useState({
    email: true,
    push: false,
    desktop: true
  });
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);

  const sections = [
    { id: 'profile', label: 'Profile', icon: <User className="w-5 h-5" /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell className="w-5 h-5" /> },
    { id: 'security', label: 'Security', icon: <Shield className="w-5 h-5" /> },
    { id: 'appearance', label: 'Appearance', icon: <Palette className="w-5 h-5" /> },
    { id: 'integrations', label: 'Integrations', icon: <Globe className="w-5 h-5" /> },
    { id: 'data', label: 'Data & Storage', icon: <Database className="w-5 h-5" /> },
  ];

  // Load user settings on component mount
  React.useEffect(() => {
    fetchUserSettings();
  }, []);

  const fetchUserSettings = async () => {
    try {
      const token = null /* DEPRECATED: Use SecureAuth.makeSecureRequest() */;
      const response = await fetch('/api/v1/settings', {
        headers: {
          'X-Requested-With': 'XMLHttpRequest' /* Uses secure cookies */,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSettings(data);
        setDarkMode(data.theme === 'dark');
        setNotifications({
          email: data.email_notifications || false,
          push: data.push_notifications || false,
          desktop: data.desktop_notifications || false
        });
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveStatus(null);
    
    try {
      const token = null /* DEPRECATED: Use SecureAuth.makeSecureRequest() */;
      const settingsData = {
        theme: darkMode ? 'dark' : 'light',
        email_notifications: notifications.email,
        push_notifications: notifications.push,
        desktop_notifications: notifications.desktop
      };

      const response = await SecureAuth.makeSecureRequest('/api/v1/settings', {
        method: 'PUT',
        body: JSON.stringify(settingsData)
      });

      if (response.ok) {
        setSaveStatus('success');
        setTimeout(() => setSaveStatus(null), 3000);
      } else {
        throw new Error('Failed to save settings');
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  const renderContent = () => {
    switch (activeSection) {
      case 'profile':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold">Profile Settings</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Profile Picture</label>
                <div className="flex items-center space-x-4">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center">
                    <User className="w-10 h-10" />
                  </div>
                  <button className="px-4 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition">
                    Change Avatar
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Full Name</label>
                <input
                  type="text"
                  placeholder="Enter your name"
                  autoComplete="name"
                  className="w-full px-4 py-2 bg-gray-900/50 border border-gray-800 rounded-lg focus:outline-none focus:border-purple-500 transition"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Email</label>
                <input
                  type="email"
                  placeholder="Enter your email"
                  autoComplete="email"
                  className="w-full px-4 py-2 bg-gray-900/50 border border-gray-800 rounded-lg focus:outline-none focus:border-purple-500 transition"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Bio</label>
                <textarea
                  placeholder="Tell us about yourself"
                  rows="4"
                  className="w-full px-4 py-2 bg-gray-900/50 border border-gray-800 rounded-lg focus:outline-none focus:border-purple-500 transition resize-none"
                />
              </div>
            </div>
          </div>
        );

      case 'notifications':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold">Notification Preferences</h2>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <div className="flex items-center space-x-3">
                  <Mail className="w-5 h-5 text-purple-400" />
                  <div>
                    <p className="font-medium">Email Notifications</p>
                    <p className="text-sm text-gray-400">Receive updates via email</p>
                  </div>
                </div>
                <button
                  onClick={() => setNotifications(prev => ({ ...prev, email: !prev.email }))}
                  className={`relative w-12 h-6 rounded-full transition ${
                    notifications.email ? 'bg-purple-600' : 'bg-gray-700'
                  }`}
                >
                  <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition transform ${
                    notifications.email ? 'translate-x-7' : 'translate-x-1'
                  }`}></div>
                </button>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <div className="flex items-center space-x-3">
                  <Smartphone className="w-5 h-5 text-purple-400" />
                  <div>
                    <p className="font-medium">Push Notifications</p>
                    <p className="text-sm text-gray-400">Receive mobile push notifications</p>
                  </div>
                </div>
                <button
                  onClick={() => setNotifications(prev => ({ ...prev, push: !prev.push }))}
                  className={`relative w-12 h-6 rounded-full transition ${
                    notifications.push ? 'bg-purple-600' : 'bg-gray-700'
                  }`}
                >
                  <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition transform ${
                    notifications.push ? 'translate-x-7' : 'translate-x-1'
                  }`}></div>
                </button>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <div className="flex items-center space-x-3">
                  <Monitor className="w-5 h-5 text-purple-400" />
                  <div>
                    <p className="font-medium">Desktop Notifications</p>
                    <p className="text-sm text-gray-400">Show desktop alerts</p>
                  </div>
                </div>
                <button
                  onClick={() => setNotifications(prev => ({ ...prev, desktop: !prev.desktop }))}
                  className={`relative w-12 h-6 rounded-full transition ${
                    notifications.desktop ? 'bg-purple-600' : 'bg-gray-700'
                  }`}
                >
                  <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition transform ${
                    notifications.desktop ? 'translate-x-7' : 'translate-x-1'
                  }`}></div>
                </button>
              </div>
            </div>
          </div>
        );

      case 'security':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold">Security Settings</h2>
            
            <div className="space-y-4">
              <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <Key className="w-5 h-5 text-purple-400" />
                    <div>
                      <p className="font-medium">Change Password</p>
                      <p className="text-sm text-gray-400">Update your password regularly</p>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </div>
              </div>

              <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <Shield className="w-5 h-5 text-purple-400" />
                    <div>
                      <p className="font-medium">Two-Factor Authentication</p>
                      <p className="text-sm text-gray-400">Add an extra layer of security</p>
                    </div>
                  </div>
                  <span className="px-2 py-1 bg-green-900/20 text-green-400 text-xs rounded">Enabled</span>
                </div>
              </div>

              <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <Lock className="w-5 h-5 text-purple-400" />
                    <div>
                      <p className="font-medium">Login Sessions</p>
                      <p className="text-sm text-gray-400">Manage your active sessions</p>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </div>
              </div>
            </div>
          </div>
        );

      case 'appearance':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold">Appearance</h2>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <div className="flex items-center space-x-3">
                  {darkMode ? <Moon className="w-5 h-5 text-purple-400" /> : <Sun className="w-5 h-5 text-yellow-400" />}
                  <div>
                    <p className="font-medium">Dark Mode</p>
                    <p className="text-sm text-gray-400">Toggle dark/light theme</p>
                  </div>
                </div>
                <button
                  onClick={() => setDarkMode(!darkMode)}
                  className={`relative w-12 h-6 rounded-full transition ${
                    darkMode ? 'bg-purple-600' : 'bg-gray-700'
                  }`}
                >
                  <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition transform ${
                    darkMode ? 'translate-x-7' : 'translate-x-1'
                  }`}></div>
                </button>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Theme Color</label>
                <div className="flex space-x-3">
                  <button className="w-10 h-10 rounded-lg bg-purple-600 border-2 border-purple-400"></button>
                  <button className="w-10 h-10 rounded-lg bg-blue-600 border-2 border-transparent hover:border-blue-400 transition"></button>
                  <button className="w-10 h-10 rounded-lg bg-green-600 border-2 border-transparent hover:border-green-400 transition"></button>
                  <button className="w-10 h-10 rounded-lg bg-red-600 border-2 border-transparent hover:border-red-400 transition"></button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Font Size</label>
                <select className="w-full px-4 py-2 bg-gray-900/50 border border-gray-800 rounded-lg focus:outline-none focus:border-purple-500 transition">
                  <option>Small</option>
                  <option>Medium</option>
                  <option>Large</option>
                </select>
              </div>
            </div>
          </div>
        );

      case 'integrations':
        return <GoogleOAuthIntegration />;

      case 'data':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold">Data & Storage</h2>
            
            <div className="space-y-4">
              <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <h3 className="font-medium mb-3">Storage Usage</h3>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Used</span>
                    <span>2.4 GB / 10 GB</span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-2">
                    <div className="bg-gradient-to-r from-purple-600 to-blue-600 h-2 rounded-full" style={{ width: '24%' }}></div>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <h3 className="font-medium mb-3">Data Management</h3>
                <div className="space-y-2">
                  <button className="w-full text-left px-4 py-2 rounded-lg hover:bg-gray-800 transition">
                    Export Data
                  </button>
                  <button className="w-full text-left px-4 py-2 rounded-lg hover:bg-gray-800 transition">
                    Clear Cache
                  </button>
                  <button className="w-full text-left px-4 py-2 rounded-lg hover:bg-gray-800 transition text-red-400">
                    Delete Account
                  </button>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none" style={{ zIndex: -1 }}>
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse delay-1000"></div>
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-gray-800 bg-black/50 backdrop-blur-lg">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                Settings
              </h1>
            </div>
            
            <button
              onClick={handleSave}
              disabled={saving}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition ${
                saving 
                  ? 'bg-gray-600 cursor-not-allowed' 
                  : saveStatus === 'success'
                  ? 'bg-green-600 hover:bg-green-700'
                  : saveStatus === 'error'
                  ? 'bg-red-600 hover:bg-red-700'
                  : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
              }`}
            >
              <Save className="w-4 h-4" />
              <span>
                {saving ? 'Saving...' : saveStatus === 'success' ? 'Saved!' : saveStatus === 'error' ? 'Error' : 'Save Changes'}
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 container mx-auto px-6 py-8">
        <div className="flex space-x-6">
          {/* Sidebar */}
          <aside className="w-64">
            <nav className="bg-gray-900/50 backdrop-blur-lg rounded-lg border border-gray-800 p-2">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${
                    activeSection === section.id
                      ? 'bg-purple-600/20 text-purple-400 border border-purple-500/30'
                      : 'hover:bg-gray-800'
                  }`}
                >
                  {section.icon}
                  <span>{section.label}</span>
                </button>
              ))}
            </nav>
          </aside>

          {/* Content Area */}
          <div className="flex-1">
            <motion.div
              key={activeSection}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className="bg-gray-900/50 backdrop-blur-lg rounded-lg border border-gray-800 p-6"
            >
              {renderContent()}
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Settings;