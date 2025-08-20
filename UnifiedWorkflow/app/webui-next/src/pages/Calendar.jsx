import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Plus,
  Clock,
  MapPin,
  Users,
  Video,
  ArrowLeft,
  Settings,
  Bell
} from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';

const Calendar = () => {
  const navigate = useNavigate();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [events, setEvents] = useState([]);
  const [view, setView] = useState('month'); // 'month', 'week', 'day'

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  useEffect(() => {
    // Fetch calendar events
    fetchEvents();
  }, [currentDate]);

  const fetchEvents = async () => {
    try {
      // Try to fetch real events from backend using unified authentication
      try {
        const response = await SecureAuth.makeSecureRequest('/api/v1/calendar/events', {
          method: 'GET'
        });

        if (response.ok) {
          const data = await response.json();
          setEvents(data.events || []);
          return;
        } else {
          console.log('Calendar API not available, using mock data');
        }
      } catch (error) {
        console.log('Calendar API error, using mock data:', error);
      }

      // Fallback to mock events if API is not available
      setEvents([
        {
          id: 1,
          title: 'Team Standup',
          time: '09:00 AM',
          type: 'video',
          attendees: 5,
          date: new Date().toISOString().split('T')[0]
        },
        {
          id: 2,
          title: 'Project Review',
          time: '02:00 PM',
          type: 'meeting',
          attendees: 3,
          date: new Date().toISOString().split('T')[0]
        }
      ]);
    } catch (error) {
      console.error('Failed to fetch events:', error);
    }
  };

  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();

    const days = [];
    
    // Add empty cells for days before month starts
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null);
    }
    
    // Add days of the month
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }

    return days;
  };

  const handlePrevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1));
  };

  const handleDateClick = (day) => {
    if (day) {
      setSelectedDate(new Date(currentDate.getFullYear(), currentDate.getMonth(), day));
    }
  };

  const isToday = (day) => {
    const today = new Date();
    return day === today.getDate() && 
           currentDate.getMonth() === today.getMonth() && 
           currentDate.getFullYear() === today.getFullYear();
  };

  const isSelected = (day) => {
    return day === selectedDate.getDate() && 
           currentDate.getMonth() === selectedDate.getMonth() && 
           currentDate.getFullYear() === selectedDate.getFullYear();
  };

  const days = getDaysInMonth(currentDate);

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
                Calendar
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* View Toggle */}
              <div className="flex items-center bg-gray-900/50 rounded-lg p-1">
                <button
                  onClick={() => setView('day')}
                  className={`px-3 py-1 rounded text-sm ${view === 'day' ? 'bg-purple-600' : 'hover:bg-gray-800'} transition`}
                >
                  Day
                </button>
                <button
                  onClick={() => setView('week')}
                  className={`px-3 py-1 rounded text-sm ${view === 'week' ? 'bg-purple-600' : 'hover:bg-gray-800'} transition`}
                >
                  Week
                </button>
                <button
                  onClick={() => setView('month')}
                  className={`px-3 py-1 rounded text-sm ${view === 'month' ? 'bg-purple-600' : 'hover:bg-gray-800'} transition`}
                >
                  Month
                </button>
              </div>

              {/* Actions */}
              <button className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition">
                <Bell className="w-5 h-5" />
              </button>
              <button className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition">
                <Settings className="w-5 h-5" />
              </button>
              <button className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg hover:from-purple-700 hover:to-blue-700 transition">
                <Plus className="w-4 h-4" />
                <span>New Event</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 container mx-auto px-6 py-8">
        <div className="flex space-x-6">
          {/* Calendar Grid */}
          <div className="flex-1">
            <div className="bg-gray-900/50 backdrop-blur-lg rounded-lg border border-gray-800 p-6">
              {/* Month Navigation */}
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold">
                  {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
                </h2>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handlePrevMonth}
                    className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => setCurrentDate(new Date())}
                    className="px-3 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 transition text-sm"
                  >
                    Today
                  </button>
                  <button
                    onClick={handleNextMonth}
                    className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Day Names */}
              <div className="grid grid-cols-7 gap-2 mb-2">
                {dayNames.map((day) => (
                  <div key={day} className="text-center text-sm font-semibold text-gray-400 py-2">
                    {day}
                  </div>
                ))}
              </div>

              {/* Calendar Days */}
              <div className="grid grid-cols-7 gap-2">
                {days.map((day, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.01 }}
                    onClick={() => handleDateClick(day)}
                    className={`
                      aspect-square flex flex-col items-center justify-center rounded-lg cursor-pointer transition
                      ${!day ? 'invisible' : ''}
                      ${isToday(day) ? 'bg-purple-600/20 border-2 border-purple-500' : ''}
                      ${isSelected(day) && !isToday(day) ? 'bg-gray-800 border border-gray-700' : ''}
                      ${!isToday(day) && !isSelected(day) && day ? 'hover:bg-gray-800/50' : ''}
                    `}
                  >
                    {day && (
                      <>
                        <span className={`text-lg ${isToday(day) ? 'font-bold text-purple-400' : ''}`}>
                          {day}
                        </span>
                        {events.some(e => {
                          const eventDay = new Date(e.date).getDate();
                          return eventDay === day;
                        }) && (
                          <div className="flex space-x-1 mt-1">
                            <div className="w-1 h-1 bg-purple-400 rounded-full"></div>
                            <div className="w-1 h-1 bg-blue-400 rounded-full"></div>
                          </div>
                        )}
                      </>
                    )}
                  </motion.div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar - Today's Events */}
          <aside className="w-80">
            <div className="bg-gray-900/50 backdrop-blur-lg rounded-lg border border-gray-800 p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                <CalendarIcon className="w-5 h-5 text-purple-400" />
                <span>Today's Schedule</span>
              </h3>
              
              <div className="space-y-3">
                {events.map((event) => (
                  <motion.div
                    key={event.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 hover:border-purple-500/50 transition"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-semibold">{event.title}</h4>
                      {event.type === 'video' ? (
                        <Video className="w-4 h-4 text-blue-400" />
                      ) : (
                        <Users className="w-4 h-4 text-purple-400" />
                      )}
                    </div>
                    <div className="space-y-1 text-sm text-gray-400">
                      <div className="flex items-center space-x-2">
                        <Clock className="w-3 h-3" />
                        <span>{event.time}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Users className="w-3 h-3" />
                        <span>{event.attendees} attendees</span>
                      </div>
                    </div>
                  </motion.div>
                ))}

                {events.length === 0 && (
                  <div className="text-center py-8 text-gray-400">
                    <CalendarIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">No events scheduled</p>
                  </div>
                )}
              </div>

              {/* Quick Actions */}
              <div className="mt-6 pt-6 border-t border-gray-800">
                <h4 className="text-sm font-semibold text-gray-400 mb-3">Quick Actions</h4>
                <div className="space-y-2">
                  <button className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition text-sm">
                    <Plus className="w-4 h-4" />
                    <span>Create Event</span>
                  </button>
                  <button className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition text-sm">
                    <Video className="w-4 h-4" />
                    <span>Schedule Meeting</span>
                  </button>
                  <button className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition text-sm">
                    <Bell className="w-4 h-4" />
                    <span>Set Reminder</span>
                  </button>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};

export default Calendar;