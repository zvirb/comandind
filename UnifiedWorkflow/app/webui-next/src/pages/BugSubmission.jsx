import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  BugAntIcon as BugIcon, 
  ExclamationTriangleIcon, 
  SparklesIcon,
  DocumentTextIcon,
  ArrowLeftIcon
} from '@heroicons/react/24/outline';

const BugSubmission = () => {
  const [formData, setFormData] = useState({
    type: 'bug',
    title: '',
    description: '',
    priority: 'medium',
    context: '',
    labels: '',
    autoAssign: true,
    createPR: true,
    runTests: true
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null);

  const templates = {
    userStory: `## User Story
As a [type of user]
I want [goal/desire]
So that [benefit/value]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes
`,
    bugReport: `## Bug Description
[Clear description of the bug]

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- OS: 
- Browser/Version: 
- Other relevant info: 
`,
    acceptance: `## Acceptance Criteria
- [ ] GIVEN [context] WHEN [action] THEN [outcome]
- [ ] GIVEN [context] WHEN [action] THEN [outcome]
- [ ] Edge case handling for [scenario]
- [ ] Performance: [metric]
- [ ] Tests written and passing
`
  };

  const insertTemplate = (templateName) => {
    setFormData(prev => ({
      ...prev,
      description: templates[templateName]
    }));
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus(null);

    try {
      // Prepare issue body
      const issueBody = `
## Request Type
${formData.type.charAt(0).toUpperCase() + formData.type.slice(1)}

## Description
${formData.description}

## Priority
${formData.priority.toUpperCase()}

## Additional Context
${formData.context || 'None provided'}

## Automation Settings
- Auto-assign Claude: ${formData.autoAssign ? 'Yes' : 'No'}
- Create PR automatically: ${formData.createPR ? 'Yes' : 'No'}
- Run tests: ${formData.runTests ? 'Yes' : 'No'}

---
*This issue was created via Claude Development Portal and will be automatically processed.*
`;

      // Prepare labels
      const labels = ['claude-auto-develop', formData.type];
      if (formData.priority === 'critical' || formData.priority === 'high') {
        labels.push('priority-' + formData.priority);
      }
      if (formData.labels) {
        labels.push(...formData.labels.split(',').map(l => l.trim()));
      }

      // Submit to bug submission service
      const response = await fetch('http://localhost:8080/api/bugs/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify({
          title: `[${formData.type.toUpperCase()}] ${formData.title}`,
          body: issueBody,
          labels: labels,
          priority: formData.priority,
          autoAssign: formData.autoAssign,
          createPR: formData.createPR,
          runTests: formData.runTests
        })
      });

      if (!response.ok) {
        throw new Error(`Submit failed: ${response.status}`);
      }

      const result = await response.json();

      setSubmitStatus({
        type: 'success',
        message: `✅ Success! Issue created: #${result.issueNumber}`,
        issueUrl: result.issueUrl
      });

      // Reset form
      setFormData({
        type: 'bug',
        title: '',
        description: '',
        priority: 'medium',
        context: '',
        labels: '',
        autoAssign: true,
        createPR: true,
        runTests: true
      });

    } catch (error) {
      setSubmitStatus({
        type: 'error',
        message: `❌ Error: ${error.message}`
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getPriorityIcon = (priority) => {
    switch (priority) {
      case 'critical':
      case 'high':
        return <ExclamationTriangleIcon className="w-4 h-4" />;
      default:
        return <BugIcon className="w-4 h-4" />;
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical':
        return 'text-red-400 bg-red-900/20';
      case 'high':
        return 'text-orange-400 bg-orange-900/20';
      case 'medium':
        return 'text-yellow-400 bg-yellow-900/20';
      case 'low':
        return 'text-green-400 bg-green-900/20';
      default:
        return 'text-gray-400 bg-gray-900/20';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-purple-900 text-white">
      {/* Header */}
      <div className="container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4 mb-8"
        >
          <button
            onClick={() => window.history.back()}
            className="p-2 rounded-lg bg-white/10 border border-white/20 hover:bg-white/20 transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            🤖 Claude Development Request Portal
          </h1>
        </motion.div>

        {/* Main Form */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="max-w-4xl mx-auto"
        >
          <div className="glass-morphism rounded-3xl p-8 border border-white/20">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Request Type */}
              <div className="space-y-4">
                <label className="block text-lg font-semibold text-white">
                  Request Type
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { value: 'feature', icon: '✨', label: 'Feature Request' },
                    { value: 'bug', icon: '🐛', label: 'Bug Fix' },
                    { value: 'refactor', icon: '🔧', label: 'Refactoring' },
                    { value: 'docs', icon: '📚', label: 'Documentation' }
                  ].map((type) => (
                    <label key={type.value} className="cursor-pointer">
                      <input
                        type="radio"
                        name="type"
                        value={type.value}
                        checked={formData.type === type.value}
                        onChange={handleInputChange}
                        className="sr-only"
                      />
                      <div className={`p-4 rounded-xl border-2 transition-all ${
                        formData.type === type.value
                          ? 'border-blue-400 bg-blue-400/10'
                          : 'border-white/20 bg-white/5 hover:border-white/40'
                      }`}>
                        <div className="text-2xl mb-2">{type.icon}</div>
                        <div className="font-medium">{type.label}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Title */}
              <div className="space-y-2">
                <label className="block text-lg font-semibold text-white">
                  Title
                  {formData.priority && (
                    <span className={`inline-flex items-center gap-1 ml-2 px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(formData.priority)}`}>
                      {getPriorityIcon(formData.priority)}
                      {formData.priority.toUpperCase()}
                    </span>
                  )}
                </label>
                <input
                  type="text"
                  name="title"
                  value={formData.title}
                  onChange={handleInputChange}
                  required
                  placeholder="Brief description of the request"
                  className="w-full p-4 rounded-xl bg-black/30 border border-white/20 text-white placeholder-gray-400 focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20 transition-all"
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <label className="block text-lg font-semibold text-white">
                  Detailed Description
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  required
                  rows={8}
                  placeholder="Provide detailed requirements, expected behavior, acceptance criteria..."
                  className="w-full p-4 rounded-xl bg-black/30 border border-white/20 text-white placeholder-gray-400 focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20 transition-all resize-vertical"
                />
                <div className="flex gap-2 flex-wrap">
                  {Object.entries({
                    userStory: 'User Story',
                    bugReport: 'Bug Report',
                    acceptance: 'Acceptance Criteria'
                  }).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => insertTemplate(key)}
                      className="px-3 py-1 text-sm rounded-full bg-purple-600/20 border border-purple-400/30 text-purple-300 hover:bg-purple-600/30 transition-colors"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Priority */}
              <div className="space-y-2">
                <label className="block text-lg font-semibold text-white">
                  Priority
                </label>
                <select
                  name="priority"
                  value={formData.priority}
                  onChange={handleInputChange}
                  className="w-full p-4 rounded-xl bg-black/30 border border-white/20 text-white focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20 transition-all"
                >
                  <option value="low">🟢 Low - Can wait</option>
                  <option value="medium">🟡 Medium - Soon</option>
                  <option value="high">🔴 High - Urgent</option>
                  <option value="critical">🚨 Critical - Immediate</option>
                </select>
              </div>

              {/* Additional Context */}
              <div className="space-y-2">
                <label className="block text-lg font-semibold text-white">
                  Additional Context <span className="text-gray-400">(optional)</span>
                </label>
                <textarea
                  name="context"
                  value={formData.context}
                  onChange={handleInputChange}
                  rows={4}
                  placeholder="Related files, dependencies, technical constraints..."
                  className="w-full p-4 rounded-xl bg-black/30 border border-white/20 text-white placeholder-gray-400 focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20 transition-all resize-vertical"
                />
              </div>

              {/* Advanced Options */}
              <div className="space-y-4 p-6 rounded-xl bg-white/5 border border-white/10">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <SparklesIcon className="w-5 h-5" />
                  Advanced Options
                </h3>
                
                <div className="space-y-2">
                  <label className="block text-white">
                    Additional Labels <span className="text-gray-400">(comma-separated)</span>
                  </label>
                  <input
                    type="text"
                    name="labels"
                    value={formData.labels}
                    onChange={handleInputChange}
                    placeholder="performance, security, ui/ux"
                    className="w-full p-3 rounded-xl bg-black/30 border border-white/20 text-white placeholder-gray-400 focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20 transition-all"
                  />
                </div>

                <div className="space-y-3">
                  {[
                    { key: 'autoAssign', label: 'Auto-assign Claude to this issue' },
                    { key: 'createPR', label: 'Automatically create PR when ready' },
                    { key: 'runTests', label: 'Run tests before creating PR' }
                  ].map((option) => (
                    <label key={option.key} className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        name={option.key}
                        checked={formData[option.key]}
                        onChange={handleInputChange}
                        className="w-5 h-5 rounded border-white/20 bg-black/30 text-blue-400 focus:ring-blue-400/20"
                      />
                      <span className="text-white">{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Submit Button */}
              <motion.button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-4 px-8 text-lg font-semibold bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 hover:shadow-[0_0_30px_rgba(59,130,246,0.5)]"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {isSubmitting ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    Submitting to Claude...
                  </div>
                ) : (
                  'Submit to Claude for Development'
                )}
              </motion.button>
            </form>

            {/* Status Message */}
            {submitStatus && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`mt-6 p-4 rounded-xl border ${
                  submitStatus.type === 'success'
                    ? 'bg-green-900/20 border-green-400/30 text-green-300'
                    : 'bg-red-900/20 border-red-400/30 text-red-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  <DocumentTextIcon className="w-5 h-5" />
                  <span>{submitStatus.message}</span>
                </div>
                {submitStatus.issueUrl && (
                  <a
                    href={submitStatus.issueUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block mt-2 text-blue-400 hover:text-blue-300 underline"
                  >
                    View Issue on GitHub →
                  </a>
                )}
              </motion.div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default BugSubmission;