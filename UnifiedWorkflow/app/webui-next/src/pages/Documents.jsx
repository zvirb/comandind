import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, 
  Upload, 
  Search, 
  Download, 
  Trash2, 
  Eye, 
  FolderOpen,
  ArrowLeft,
  Grid,
  List,
  Filter,
  Plus
} from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';

const Documents = () => {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [selectedCategory, setSelectedCategory] = useState('all');

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      // Use unified backend authentication via SecureAuth
      const response = await SecureAuth.makeSecureRequest('/api/v1/documents', {
        method: 'GET'
      });

      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      } else {
        console.error('Failed to fetch documents:', response.status);
        // Don't redirect to login - SecureAuth.makeSecureRequest handles auth errors
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
      // SecureAuth.makeSecureRequest already handles 401 redirects
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Use unified backend authentication via SecureAuth
      const response = await SecureAuth.makeSecureRequest('/api/v1/documents/upload', {
        method: 'POST',
        body: formData
        // Note: headers automatically handled by SecureAuth for FormData
      });

      if (response.ok) {
        await fetchDocuments();
      } else {
        console.error('Failed to upload document:', response.status);
      }
    } catch (error) {
      console.error('Failed to upload document:', error);
    }
  };

  const filteredDocuments = documents.filter(doc => 
    doc.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const categories = [
    { id: 'all', name: 'All Documents', icon: <FolderOpen className="w-4 h-4" /> },
    { id: 'recent', name: 'Recent', icon: <FileText className="w-4 h-4" /> },
    { id: 'shared', name: 'Shared', icon: <FileText className="w-4 h-4" /> },
  ];

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
                Documents
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Search Bar */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search documents..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  autoComplete="off"
                  className="pl-10 pr-4 py-2 bg-gray-900/50 border border-gray-800 rounded-lg focus:outline-none focus:border-purple-500 transition w-64"
                />
              </div>

              {/* View Mode Toggle */}
              <div className="flex items-center bg-gray-900/50 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 rounded ${viewMode === 'grid' ? 'bg-purple-600' : 'hover:bg-gray-800'} transition`}
                >
                  <Grid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-2 rounded ${viewMode === 'list' ? 'bg-purple-600' : 'hover:bg-gray-800'} transition`}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>

              {/* Upload Button */}
              <label className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg hover:from-purple-700 hover:to-blue-700 transition cursor-pointer">
                <Upload className="w-4 h-4" />
                <span>Upload</span>
                <input
                  type="file"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 container mx-auto px-6 py-8">
        <div className="flex space-x-6">
          {/* Sidebar */}
          <aside className="w-64">
            <div className="bg-gray-900/50 backdrop-blur-lg rounded-lg border border-gray-800 p-4">
              <h3 className="text-sm font-semibold text-gray-400 mb-4">Categories</h3>
              <nav className="space-y-2">
                {categories.map((category) => (
                  <button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition ${
                      selectedCategory === category.id
                        ? 'bg-purple-600/20 text-purple-400 border border-purple-500/30'
                        : 'hover:bg-gray-800'
                    }`}
                  >
                    {category.icon}
                    <span className="text-sm">{category.name}</span>
                  </button>
                ))}
              </nav>
            </div>

            {/* Quick Stats */}
            <div className="bg-gray-900/50 backdrop-blur-lg rounded-lg border border-gray-800 p-4 mt-4">
              <h3 className="text-sm font-semibold text-gray-400 mb-4">Storage</h3>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-400">Used</span>
                    <span className="text-gray-300">2.4 GB / 10 GB</span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-2">
                    <div className="bg-gradient-to-r from-purple-600 to-blue-600 h-2 rounded-full" style={{ width: '24%' }}></div>
                  </div>
                </div>
                <div className="text-xs text-gray-500">
                  {filteredDocuments.length} documents
                </div>
              </div>
            </div>
          </aside>

          {/* Documents Grid/List */}
          <div className="flex-1">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : filteredDocuments.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-16"
              >
                <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">No documents yet</h3>
                <p className="text-gray-400 mb-6">Upload your first document to get started</p>
                <label className="inline-flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg hover:from-purple-700 hover:to-blue-700 transition cursor-pointer">
                  <Plus className="w-5 h-5" />
                  <span>Upload Document</span>
                  <input
                    type="file"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </motion.div>
            ) : (
              <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-3'}>
                {filteredDocuments.map((doc, index) => (
                  <motion.div
                    key={doc.id || index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={`bg-gray-900/50 backdrop-blur-lg rounded-lg border border-gray-800 hover:border-purple-500/50 transition ${
                      viewMode === 'list' ? 'flex items-center justify-between p-4' : 'p-6'
                    }`}
                  >
                    {viewMode === 'grid' ? (
                      <>
                        <div className="flex items-center justify-between mb-4">
                          <FileText className="w-8 h-8 text-purple-400" />
                          <div className="flex space-x-2">
                            <button className="p-2 rounded hover:bg-gray-800 transition">
                              <Eye className="w-4 h-4" />
                            </button>
                            <button className="p-2 rounded hover:bg-gray-800 transition">
                              <Download className="w-4 h-4" />
                            </button>
                            <button className="p-2 rounded hover:bg-red-900/20 text-red-400 transition">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                        <h3 className="font-semibold mb-1 truncate">{doc.name || 'Untitled'}</h3>
                        <p className="text-sm text-gray-400 mb-2">{doc.size || '0 KB'}</p>
                        <p className="text-xs text-gray-500">{doc.modified || 'Recently'}</p>
                      </>
                    ) : (
                      <>
                        <div className="flex items-center space-x-4">
                          <FileText className="w-6 h-6 text-purple-400" />
                          <div>
                            <h3 className="font-semibold">{doc.name || 'Untitled'}</h3>
                            <p className="text-sm text-gray-400">{doc.size || '0 KB'} • {doc.modified || 'Recently'}</p>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <button className="p-2 rounded hover:bg-gray-800 transition">
                            <Eye className="w-4 h-4" />
                          </button>
                          <button className="p-2 rounded hover:bg-gray-800 transition">
                            <Download className="w-4 h-4" />
                          </button>
                          <button className="p-2 rounded hover:bg-red-900/20 text-red-400 transition">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Documents;