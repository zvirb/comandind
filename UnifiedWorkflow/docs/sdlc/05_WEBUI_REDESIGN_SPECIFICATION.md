# AIWFE WebUI Redesign Specification

## Document Information

**Document Version**: 1.0  
**Date**: August 12, 2025  
**Authors**: UI/UX Lead, Frontend Architect  
**Reviewers**: Design Team, Technical Team  
**Status**: Draft for Review  

## 1. Executive Summary

This document outlines the comprehensive redesign of the AIWFE WebUI, transforming from the current Svelte implementation to a modern React/Next.js PWA inspired by the aesthetic and interaction patterns of cosmos.so and micro.so. The redesign aligns with the provided wireframe specifications while incorporating modern productivity paradigms and seamless integration with the new smart agentic system.

## 2. Design Philosophy and Inspiration

### 2.1 Cosmos.so Aesthetic Inspiration

#### Key Design Elements
```yaml
Visual Language:
  - Minimalist, clean interface with purposeful white space
  - Black and white color scheme with selective color accents
  - Typography-focused design with Inter font family
  - Grid-based layouts with organic, flowing elements
  - Subtle animations and micro-interactions

Interaction Patterns:
  - Drag-to-explore navigation
  - Smooth hover states and transitions
  - Card-based content organization
  - Tag-based categorization system
  - Search-first interaction model

Content Philosophy:
  - "Zero noise or distractions"
  - Focus on harmonious expression
  - Content-first approach
  - Collaborative by design
```

#### Implementation Translation
```css
/* Cosmos-inspired Typography */
.cosmos-heading {
  font-family: 'Inter', -apple-system, sans-serif;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.025em;
  color: #000000;
}

.cosmos-body {
  font-family: 'Inter', -apple-system, sans-serif;
  font-weight: 400;
  line-height: 1.6;
  color: #333333;
}

/* Cosmos-inspired Animations */
@keyframes cosmos-appear {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.cosmos-card {
  animation: cosmos-appear 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.cosmos-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}
```

### 2.2 Micro.so Functionality Inspiration

#### Productivity Paradigms
```yaml
Organizational Philosophy:
  - "Organized. So you don't have to be."
  - Automatic organization and intelligence
  - Centralized workspace concept
  - AI-powered automation
  - Context-aware suggestions

Interface Patterns:
  - All-in-one tool mentality
  - Tabbed navigation system
  - Contextual sidebars
  - Automated data enrichment
  - Collaborative features built-in

Visual Elements:
  - Gradient backgrounds and modern styling
  - Card-based information hierarchy
  - Status indicators and progress tracking
  - Real-time collaboration indicators
  - Professional, business-focused aesthetics
```

#### Implementation Translation
```css
/* Micro-inspired Gradients */
.micro-gradient {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.micro-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
}

/* Micro-inspired Status Indicators */
.status-active {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.status-pending {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}
```

### 2.3 Blending Our Design Inspirations

#### Harmonizing Cosmos and Micro Aesthetics

Our approach strategically combines the best elements from both cosmos.so and micro.so by using **layered application** of their design philosophies:

**Foundation Layer - Cosmos Aesthetic**:
- **Typography-focused layouts** serve as the structural backbone
- **Minimalist white space** creates breathing room and clarity
- **Clean, uncluttered navigation** maintains focus and reduces cognitive load
- **Black and white base palette** ensures readability and professional appearance

**Enhancement Layer - Micro Aesthetic**:
- **Gradient accents** applied strategically to status indicators, progress bars, and interactive elements
- **Contextual sidebars** appear in data-dense views like Opportunities and Calendar pages
- **Smart automation indicators** use subtle color coding to show AI-powered features
- **Business-focused density** in areas where power users need comprehensive information

**Integration Strategy**:
```yaml
Content-First Pages (Landing, Login):
  Base: Cosmos minimalism with spacious layouts
  Accent: Micro gradients for CTAs and status elements

Productivity Pages (Dashboard, Opportunities):
  Base: Cosmos typography and structure
  Enhancement: Micro density and gradient-coded organization

Power-User Views (Calendar, Settings):
  Base: Cosmos clarity and focus
  Enhancement: Micro contextual sidebars and intelligent indicators
```

This approach ensures that newcomers experience the calming, focused aesthetic of Cosmos while power users gain access to the rich, data-dense features inspired by Micro's productivity paradigms.

### 2.4 Wireframe Integration and Design Decisions

#### Wireframe Analysis and Implementation

Based on the provided wireframe.pdf, the following key pages and interactions are identified with detailed implementation clarifications:

**Landing Page (Page 1)**:
- Hero section with **motion-reactive image** that responds to mouse movement on desktop and gyroscope data on mobile devices
- **Zoom-in and fade scroll effect**: As users scroll past the hero section, the main image will simultaneously zoom in and fade out
- Task examples section with **staggered animations**
- Chat example demonstration with **typewriter effects**

**Dashboard Wireframe (Page 6)**:
- Navigation bar with multiple sections and **collapsible functionality**
- Today's tasks and upcoming items with **real-time updates**
- Recent chats section with **quick access links**
- Weather and stats integration with **live data sync**
- Calendar links and opportunities links with **contextual previews**
- **Scroll-to-chat mechanism**: The main dashboard content is scrollable, and scrolling past the primary widgets transitions the view into a 'New Chat' interface, providing seamless entry into the AIWFE chat system

**Opportunities Wireframe (Page 8) - Design Philosophy Decision**:
> **Implementation Choice Rationale**: The wireframe depicts a free-form, node-based layout suggesting tasks can be linked organically like a mind map. However, our implementation translates this into a structured Kanban-style system for the following reasons:
> - **User Familiarity**: Kanban boards are widely understood in productivity applications
> - **Scalability**: Structured columns handle large task volumes better than free-form layouts
> - **Mobile Responsiveness**: Kanban columns adapt better to mobile screens
> - **Future Enhancement**: We can add a "Mind Map View" toggle as an advanced feature using react-flow
- Sticky note style task cards with **drag-and-drop** functionality
- Create new task functionality with **slide-in modals**
- Task list at bottom with **collapsible panels**
- **Links to Reflections**: Navigation includes reflection tracking and review functionality

**Login Wireframe (Page 5)**:
- Collapsible navigation bar with **smooth transitions**
- Username/password with **progressive 2FA**: Upon successful password entry, the 2FA input field will animate by sliding up from the bottom
- Social login options with **OAuth integration**
- Register link integration with **seamless form transitions**

## 3. Technical Architecture

### 3.1 Technology Stack

#### Core Framework
```yaml
Frontend Framework: Next.js 14+ with App Router
Language: TypeScript 5.0+
Styling: Tailwind CSS 3.4+ with custom design system
UI Components: Headless UI + Custom component library
State Management: Zustand + React Query (TanStack Query)
Animation: Framer Motion + CSS transitions
Authentication: NextAuth.js v5 with OAuth providers
PWA: Next.js PWA plugin with workbox
Testing: Jest + React Testing Library + Playwright
Build Tools: Turbopack (Next.js built-in)
```

#### Component Architecture
```yaml
Design System:
  - Atomic design methodology
  - Component composition patterns
  - Theme-based styling system
  - Responsive design tokens
  - Accessibility-first approach

State Management:
  - Global state with Zustand
  - Server state with React Query
  - Form state with React Hook Form
  - URL state with Next.js router
  - Local state with React hooks

State Management Boundaries and Examples:
  Global State (Zustand):
    - UI preferences: theme, sidebar collapsed state, notification settings
    - User session: current user data, authentication status
    - Application state: active chat thread, current page context
    - Transient UI state: modal open/closed, loading overlays
    
  Server State (React Query):
    - API data: tasks list, calendar events, chat history
    - User profile: settings, preferences, integrations
    - Real-time data: notifications, status updates, live metrics
    - Background sync: offline queue, cache invalidation
    
  Form State (React Hook Form):
    - Task creation/editing forms
    - User profile updates
    - Settings configurations
    - Search and filter inputs
    
  URL State (Next.js Router):
    - Current page and route parameters
    - Query parameters for search/filter states
    - Deep-linkable application state
```

### 3.2 Project Structure

```
webui-next/
├── public/                     # Static assets
│   ├── icons/                 # PWA icons and favicons
│   ├── images/               # Static images
│   └── manifest.json         # PWA manifest
├── src/
│   ├── app/                  # Next.js App Router
│   │   ├── (auth)/          # Authentication routes
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── layout.tsx
│   │   ├── dashboard/       # Main dashboard
│   │   │   ├── page.tsx
│   │   │   └── loading.tsx
│   │   ├── opportunities/   # Project management
│   │   │   ├── page.tsx
│   │   │   ├── [id]/
│   │   │   └── components/
│   │   ├── calendar/        # Calendar integration
│   │   │   ├── page.tsx
│   │   │   └── components/
│   │   ├── chat/           # AIWFE chat interface
│   │   │   ├── page.tsx
│   │   │   ├── [chatId]/
│   │   │   └── components/
│   │   ├── settings/       # User settings
│   │   │   ├── page.tsx
│   │   │   ├── profile/
│   │   │   ├── integrations/
│   │   │   └── preferences/
│   │   ├── globals.css     # Global styles
│   │   ├── layout.tsx      # Root layout
│   │   ├── loading.tsx     # Global loading UI
│   │   ├── error.tsx       # Global error UI
│   │   ├── not-found.tsx   # 404 page
│   │   └── page.tsx        # Landing page
│   ├── components/
│   │   ├── ui/             # Base UI components
│   │   │   ├── button/
│   │   │   ├── card/
│   │   │   ├── dialog/
│   │   │   ├── input/
│   │   │   ├── navigation/
│   │   │   └── layout/
│   │   ├── features/       # Feature-specific components
│   │   │   ├── auth/
│   │   │   ├── dashboard/
│   │   │   ├── opportunities/
│   │   │   ├── calendar/
│   │   │   ├── chat/
│   │   │   └── settings/
│   │   └── providers/      # Context providers
│   ├── lib/
│   │   ├── api/           # API client and utilities
│   │   │   ├── client.ts
│   │   │   ├── types.ts
│   │   │   ├── hooks/
│   │   │   └── queries/
│   │   ├── auth/          # Authentication utilities
│   │   │   ├── config.ts
│   │   │   ├── providers.ts
│   │   │   └── middleware.ts
│   │   ├── utils/         # Utility functions
│   │   │   ├── cn.ts
│   │   │   ├── format.ts
│   │   │   ├── validation.ts
│   │   │   └── constants.ts
│   │   ├── stores/        # Zustand stores
│   │   │   ├── auth.ts
│   │   │   ├── ui.ts
│   │   │   ├── chat.ts
│   │   │   └── opportunities.ts
│   │   └── hooks/         # Custom React hooks
│   ├── styles/
│   │   ├── globals.css    # Global CSS
│   │   ├── components.css # Component-specific styles
│   │   └── animations.css # Animation definitions
│   └── types/
│       ├── auth.ts
│       ├── api.ts
│       ├── ui.ts
│       └── global.ts
├── docs/
│   ├── SETUP.md
│   ├── COMPONENTS.md
│   └── DEPLOYMENT.md
├── tests/
│   ├── __mocks__/
│   ├── components/
│   ├── pages/
│   └── e2e/
├── .env.local
├── .env.example
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
├── jest.config.js
├── playwright.config.ts
└── package.json
```

### 3.3 Advanced Technical Integration

#### Error Boundary Implementation
```tsx
// Global Error Boundary
class GlobalErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log to monitoring service
    console.error('Global Error:', error, errorInfo);
    
    // Send to error tracking (Sentry, etc.)
    if (typeof window !== 'undefined') {
      window.gtag?.('event', 'exception', {
        description: error.toString(),
        fatal: false
      });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center p-8">
            <h1 className="text-2xl font-semibold mb-4">Something went wrong</h1>
            <p className="text-gray-600 mb-6">
              We apologize for the inconvenience. Please try refreshing the page.
            </p>
            <Button onClick={() => window.location.reload()}>
              Refresh Page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Feature-specific Error Boundaries
const ChatErrorBoundary = ({ children }) => (
  <ErrorBoundary fallback={<ChatErrorFallback />}>
    {children}
  </ErrorBoundary>
);
```

#### WebSocket Integration Architecture
```typescript
// Real-time Connection Manager
class WebSocketManager {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000;

  connect(url: string) {
    this.socket = new WebSocket(url);
    
    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.socket.onclose = () => {
      this.handleReconnect();
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private handleMessage(data: any) {
    switch (data.type) {
      case 'TASK_UPDATE':
        // Update task state
        queryClient.invalidateQueries(['tasks']);
        break;
      case 'NEW_MESSAGE':
        // Update chat state
        queryClient.setQueryData(['messages', data.chatId], (old: any) => 
          [...(old || []), data.message]
        );
        break;
      case 'NOTIFICATION':
        // Show notification
        toast(data.message);
        break;
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect(this.socket?.url || '');
      }, this.reconnectInterval * Math.pow(2, this.reconnectAttempts));
    }
  }
}

// React Hook for WebSocket
const useWebSocket = (url: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const wsManager = useRef(new WebSocketManager());

  useEffect(() => {
    wsManager.current.connect(url);
    setIsConnected(true);

    return () => {
      wsManager.current.disconnect();
      setIsConnected(false);
    };
  }, [url]);

  return { isConnected };
};
```

#### API Contract Definitions
```typescript
// Type-safe API Client
interface APIEndpoints {
  // Authentication
  'POST /auth/login': {
    body: { email: string; password: string; }
    response: { token: string; user: User; }
  }
  
  // Tasks
  'GET /tasks': {
    query?: { status?: TaskStatus; limit?: number; }
    response: { tasks: Task[]; total: number; }
  }
  'POST /tasks': {
    body: CreateTaskRequest
    response: Task
  }
  'PUT /tasks/:id': {
    params: { id: string }
    body: UpdateTaskRequest
    response: Task
  }
  
  // Chat
  'GET /chat/conversations': {
    response: ChatConversation[]
  }
  'POST /chat/messages': {
    body: { conversationId: string; message: string; }
    response: { message: ChatMessage; aiResponse: ChatMessage; }
  }
  
  // Calendar
  'GET /calendar/events': {
    query: { start: string; end: string; }
    response: CalendarEvent[]
  }
}

// Type-safe API client generator
const createAPIClient = <T extends keyof APIEndpoints>(
  baseURL: string
) => ({
  async request<K extends keyof APIEndpoints>(
    endpoint: K,
    options: APIEndpoints[K] extends { body: any } 
      ? { body: APIEndpoints[K]['body'] } & Partial<Omit<RequestInit, 'body'>>
      : Partial<RequestInit>
  ): Promise<APIEndpoints[K]['response']> {
    // Implementation with full type safety
  }
});

// Usage
const api = createAPIClient<APIEndpoints>('/api');
const tasks = await api.request('GET /tasks', { 
  query: { status: 'pending' } 
}); // Fully typed response
```

#### Integration Patterns
```yaml
AIWFE Backend Integration:
  Authentication: JWT tokens with refresh mechanism
  Real-time Updates: WebSocket connection for live data
  API Versioning: /api/v1/ with backward compatibility
  Error Handling: Structured error responses with codes
  
Google Services Integration:
  Calendar: OAuth 2.0 with service account fallback
  Drive: File picker integration for attachments
  Gmail: Email notifications and thread management
  
Pieces Integration:
  Code Snippets: Bi-directional sync with Pieces OS
  Context Sharing: Automatic context capture and sharing
  Search Integration: Unified search across all sources
```

## 4. Page-by-Page Design Specifications

### 4.1 Landing Page

#### Design Concept
Inspired by cosmos.so's discovery-focused landing with micro.so's productivity messaging.

#### Layout Structure
```yaml
Hero Section:
  - Large, impactful headline with gradient text
  - Subtitle emphasizing AI-powered workflow automation
  - Animated background with floating elements
  - Primary CTA button with smooth hover effects
  - Hero image showcasing the dashboard interface

Value Proposition:
  - Three-column feature highlight
  - Animated icons and descriptions
  - Real-time screenshot carousel
  - Customer testimonial integration

Product Demo:
  - Interactive dashboard preview
  - Zoom-in animations on scroll
  - Task management showcase
  - Chat interface demonstration

Footer:
  - Clean, minimal footer design
  - Social links and contact information
  - Newsletter signup integration
```

#### Implementation Example
```tsx
// Landing Page Component
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-gray-50">
      <HeroSection />
      <FeatureShowcase />
      <ProductDemo />
      <TestimonialSection />
      <CTASection />
      <Footer />
    </div>
  );
}

const HeroSection = () => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const updateMousePosition = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };
    
    const updateScrollY = () => setScrollY(window.scrollY);

    window.addEventListener('mousemove', updateMousePosition);
    window.addEventListener('scroll', updateScrollY);
    
    return () => {
      window.removeEventListener('mousemove', updateMousePosition);
      window.removeEventListener('scroll', updateScrollY);
    };
  }, []);

  // Motion-reactive parallax effect
  const parallaxStyle = {
    transform: `translate3d(${mousePosition.x * 0.02}px, ${mousePosition.y * 0.02}px, 0)`,
  };

  // Zoom and fade scroll effect
  const scrollEffectStyle = {
    transform: `scale(${1 + scrollY * 0.001}) translateY(${scrollY * 0.5}px)`,
    opacity: Math.max(0, 1 - scrollY * 0.003),
  };

  return (
    <section className="relative py-20 overflow-hidden">
      <div className="container mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center"
        >
          <h1 className="text-6xl font-bold mb-6">
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Organized.
            </span>
            <br />
            So you don't have to be.
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            AIWFE is an AI-powered workflow engine that automatically organizes 
            your tasks, manages your calendar, and enhances your productivity.
          </p>
          <Button size="lg" className="cosmos-button">
            Get Started
          </Button>
        </motion.div>
      </div>
      
      {/* Motion-reactive hero image */}
      <motion.div 
        className="absolute top-20 right-10 w-96 h-96"
        style={parallaxStyle}
      >
        <div 
          className="dashboard-preview"
          style={scrollEffectStyle}
        >
          <Image
            src="/images/dashboard-preview.png"
            alt="AIWFE Dashboard Preview"
            width={384}
            height={384}
            className="rounded-xl shadow-2xl"
          />
        </div>
      </motion.div>
      
      <FloatingElements />
    </section>
  );
};
```

### 4.2 Dashboard Page

#### Wireframe Implementation
Based on Page 6 of the wireframe, implementing a unified dashboard view.

#### Layout Structure
```yaml
Navigation:
  - Collapsible navigation bar (matches wireframe)
  - Quick access icons (home, calendar, opportunities, chat)
  - User profile dropdown
  - Settings access
  - Notification indicator

Main Dashboard:
  - Today section with upcoming tasks
  - Recent chats sidebar
  - Weather widget integration
  - Statistics cards
  - Quick action buttons

Sidebar Areas:
  - Calendar integration preview
  - Opportunities link
  - Recent activity feed
  - Quick search functionality
```

#### Implementation
```tsx
const DashboardPage = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="flex">
        <Sidebar />
        <MainContent />
        <RightSidebar />
      </div>
    </div>
  );
};

const MainContent = () => {
  const [scrollPosition, setScrollPosition] = useState(0);
  const contentRef = useRef(null);

  useEffect(() => {
    const handleScroll = () => {
      if (contentRef.current) {
        setScrollPosition(contentRef.current.scrollTop);
      }
    };

    const element = contentRef.current;
    if (element) {
      element.addEventListener('scroll', handleScroll);
      return () => element.removeEventListener('scroll', handleScroll);
    }
  }, []);

  // Scroll-to-chat threshold (when widgets are scrolled past)
  const chatTransitionThreshold = 800;
  const showChatInterface = scrollPosition > chatTransitionThreshold;

  return (
    <main 
      ref={contentRef}
      className="flex-1 p-6 overflow-y-auto h-screen"
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <TodaySection className="lg:col-span-2" />
        <StatsSection />
        <RecentChats />
        <WeatherWidget />
        <UpcomingTasks />
      </div>
      
      {/* Scroll-to-Chat Transition */}
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ 
          opacity: showChatInterface ? 1 : 0,
          y: showChatInterface ? 0 : 50 
        }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="mt-12 min-h-screen"
      >
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-4">Start New Chat</h2>
            <p className="text-gray-600">
              Continue your workflow with AI assistance
            </p>
          </div>
          <ChatInterface embedded={true} />
        </div>
      </motion.div>
    </main>
  );
};

const TodaySection = ({ className }: { className?: string }) => (
  <Card className={cn("p-6", className)}>
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-2xl font-semibold">Today</h2>
      <Button variant="outline" size="sm">
        View All
      </Button>
    </div>
    <TaskList tasks={todayTasks} />
  </Card>
);
```

### 4.3 Opportunities Page

#### Wireframe Implementation
Based on Page 8 wireframe, implementing Kanban-style project management.

#### Layout Structure
```yaml
Navigation:
  - Same navigation as dashboard
  - Breadcrumb navigation
  - View toggle (Kanban/List/Calendar)

Opportunity Board:
  - Sticky note style task cards
  - Drag and drop functionality
  - Status columns (Pending, In Progress, Completed)
  - Add new opportunity button

Task Management:
  - Task creation modal
  - Task details sidebar
  - File attachment support
  - Due date management
  - Priority indicators

Bottom Panel:
  - Task list view
  - Filter and search options
  - Bulk actions
  - Export functionality
```

#### Implementation
```tsx
const OpportunitiesPage = () => {
  const [view, setView] = useState<'kanban' | 'list'>('kanban');
  
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="p-6">
        <PageHeader />
        <ViewToggle view={view} onChange={setView} />
        {view === 'kanban' ? <KanbanBoard /> : <ListView />}
      </div>
    </div>
  );
};

const KanbanBoard = () => (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
    <KanbanColumn 
      title="Pending" 
      color="yellow"
      opportunities={pendingOpportunities}
    />
    <KanbanColumn 
      title="In Progress" 
      color="blue"
      opportunities={inProgressOpportunities}
    />
    <KanbanColumn 
      title="Completed" 
      color="green"
      opportunities={completedOpportunities}
    />
  </div>
);

const KanbanColumn = ({ title, color, opportunities }) => (
  <div className="bg-white rounded-lg p-4">
    <h3 className={`text-lg font-semibold mb-4 text-${color}-600`}>
      {title} ({opportunities.length})
    </h3>
    <Droppable droppableId={title.toLowerCase()}>
      {(provided) => (
        <div {...provided.droppableProps} ref={provided.innerRef}>
          {opportunities.map((opportunity, index) => (
            <OpportunityCard 
              key={opportunity.id}
              opportunity={opportunity}
              index={index}
            />
          ))}
          {provided.placeholder}
        </div>
      )}
    </Droppable>
    <AddOpportunityButton />
  </div>
);
```

### 4.4 Calendar Page

#### Design Concept
Google Calendar integration with AIWFE intelligence overlay.

#### Layout Structure
```yaml
Calendar Header:
  - Month/week/day view toggles
  - Navigation arrows
  - Today button
  - Add event button

Calendar Grid:
  - Full calendar view with events
  - Task integration
  - Opportunity deadlines
  - Meeting suggestions

Sidebar:
  - Upcoming events
  - Task deadlines
  - Meeting preparation
  - Calendar sync status

Intelligence Features:
  - Smart scheduling suggestions
  - Conflict detection
  - Travel time calculation
  - Meeting preparation reminders
```

### 4.5 Chat Interface

#### Design Concept
AIWFE-powered conversational interface with modern chat UX.

#### Layout Structure
```yaml
Chat Header:
  - Current chat title
  - Agent status indicator
  - Settings menu
  - Search functionality

Message Area:
  - Message bubbles with user/agent distinction
  - Code syntax highlighting
  - File sharing support
  - Rich media support

Input Area:
  - Text input with markdown support
  - File attachment button
  - Voice input support
  - Send button with keyboard shortcuts

Sidebar:
  - Chat history
  - Saved snippets
  - Context information
  - Pieces integration
```

### 4.6 Settings Page

#### Design Concept
Comprehensive settings interface with modern tabbed navigation for user preferences, integrations, and system configuration.

#### Layout Structure
```yaml
Settings Navigation:
  - Tabbed navigation (Profile, Preferences, Integrations, Advanced)
  - Search functionality for settings
  - Reset to defaults option
  - Save/cancel actions

Profile Settings:
  - User information management
  - Avatar upload and display
  - Contact information
  - Role and permissions display

Preferences Tab:
  - Theme selection (light/dark/auto)
  - Language preferences
  - Timezone configuration
  - Notification settings
  - Email preferences

Integrations Tab:
  - Google Workspace configuration
  - Pieces OS/Developers connectivity
  - Slack integration settings
  - Third-party service connections
  - API key management

Intelligent Scoring Configuration:
  - AI scoring weights adjustment
  - Business Value weighting (default: 40%)
  - Feasibility weighting (default: 30%)
  - Competitive weighting (default: 20%)
  - Engagement weighting (default: 10%)
  - Custom scoring factors
  - Scoring algorithm selection
  - Performance analytics display

Advanced Settings:
  - Data export/import
  - Security settings
  - Performance preferences
  - Developer mode options
  - Debug information
```

#### Implementation Example
```tsx
const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('profile');
  const [scoringWeights, setScoringWeights] = useState({
    businessValue: 40,
    feasibility: 30,
    competitive: 20,
    engagement: 10
  });

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Settings</h1>
        <p className="text-gray-600">Manage your account preferences and configurations</p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6" aria-label="Settings">
            {['profile', 'preferences', 'integrations', 'advanced'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'integrations' && (
            <div className="space-y-8">
              <ScoringConfigurationSection 
                weights={scoringWeights}
                onWeightsChange={setScoringWeights}
              />
              <IntegrationsSection />
            </div>
          )}
          {/* Other tab content */}
        </div>
      </div>
    </div>
  );
};

const ScoringConfigurationSection = ({ weights, onWeightsChange }) => {
  const handleWeightChange = (factor: string, value: number) => {
    onWeightsChange(prev => ({ ...prev, [factor]: value }));
  };

  return (
    <div className="bg-gray-50 rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">Intelligent Scoring Configuration</h3>
      <p className="text-gray-600 mb-6">
        Adjust the weighting factors for AI-powered opportunity scoring algorithm.
      </p>
      
      <div className="space-y-4">
        {Object.entries(weights).map(([factor, weight]) => (
          <div key={factor} className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700 capitalize">
              {factor.replace(/([A-Z])/g, ' $1')} Score
            </label>
            <div className="flex items-center space-x-4">
              <input
                type="range"
                min="0"
                max="100"
                value={weight}
                onChange={(e) => handleWeightChange(factor, parseInt(e.target.value))}
                className="w-32"
              />
              <span className="text-sm font-medium w-12 text-right">{weight}%</span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium">Total:</span>
          <span className="text-sm font-bold">
            {Object.values(weights).reduce((sum, weight) => sum + weight, 0)}%
          </span>
        </div>
      </div>
    </div>
  );
};
```

## 5. Design System Specification

### 5.1 Color Palette

#### Primary Colors
```css
:root {
  /* Cosmos-inspired neutrals */
  --cosmos-black: #000000;
  --cosmos-white: #ffffff;
  --cosmos-gray-50: #fafafa;
  --cosmos-gray-100: #f5f5f5;
  --cosmos-gray-200: #e5e5e5;
  --cosmos-gray-300: #d4d4d4;
  --cosmos-gray-400: #a3a3a3;
  --cosmos-gray-500: #737373;
  --cosmos-gray-600: #525252;
  --cosmos-gray-700: #404040;
  --cosmos-gray-800: #262626;
  --cosmos-gray-900: #171717;

  /* Micro-inspired accent colors */
  --micro-blue-50: #eff6ff;
  --micro-blue-500: #3b82f6;
  --micro-blue-600: #2563eb;
  --micro-blue-700: #1d4ed8;
  
  --micro-purple-50: #faf5ff;
  --micro-purple-500: #8b5cf6;
  --micro-purple-600: #7c3aed;
  --micro-purple-700: #6d28d9;

  /* Status colors */
  --status-success: #10b981;
  --status-warning: #f59e0b;
  --status-error: #ef4444;
  --status-info: #3b82f6;
}
```

#### Color Usage Guidelines
```yaml
Text:
  - Primary: cosmos-gray-900
  - Secondary: cosmos-gray-600
  - Muted: cosmos-gray-500
  - Inverted: cosmos-white

Backgrounds:
  - Primary: cosmos-white
  - Secondary: cosmos-gray-50
  - Elevated: cosmos-white with shadow

Accents:
  - Primary: micro-blue-600
  - Secondary: micro-purple-600
  - Interactive: micro-blue-500
```

### 5.2 Typography System

#### Font Stack
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Typography Scale */
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-base { font-size: 1rem; line-height: 1.5rem; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-xl { font-size: 1.25rem; line-height: 1.75rem; }
.text-2xl { font-size: 1.5rem; line-height: 2rem; }
.text-3xl { font-size: 1.875rem; line-height: 2.25rem; }
.text-4xl { font-size: 2.25rem; line-height: 2.5rem; }
.text-5xl { font-size: 3rem; line-height: 1; }
.text-6xl { font-size: 3.75rem; line-height: 1; }
```

#### Typography Components
```tsx
const Typography = {
  H1: ({ children, className, ...props }) => (
    <h1 className={cn("text-4xl md:text-5xl font-bold tracking-tight", className)} {...props}>
      {children}
    </h1>
  ),
  
  H2: ({ children, className, ...props }) => (
    <h2 className={cn("text-3xl md:text-4xl font-semibold tracking-tight", className)} {...props}>
      {children}
    </h2>
  ),
  
  Body: ({ children, className, ...props }) => (
    <p className={cn("text-base text-gray-600 leading-relaxed", className)} {...props}>
      {children}
    </p>
  ),
  
  Caption: ({ children, className, ...props }) => (
    <span className={cn("text-sm text-gray-500", className)} {...props}>
      {children}
    </span>
  )
};
```

### 5.3 Component Library

#### Button Components
```tsx
const Button = ({ 
  variant = 'primary', 
  size = 'md', 
  children, 
  className,
  ...props 
}) => {
  const baseClasses = "inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2";
  
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",
    secondary: "bg-white text-gray-900 border border-gray-300 hover:bg-gray-50 focus:ring-blue-500",
    ghost: "text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:ring-blue-500"
  };
  
  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2 text-base",
    lg: "px-6 py-3 text-lg"
  };
  
  return (
    <button 
      className={cn(baseClasses, variants[variant], sizes[size], className)}
      {...props}
    >
      {children}
    </button>
  );
};
```

#### Card Components
```tsx
const Card = ({ children, className, ...props }) => (
  <div 
    className={cn(
      "bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden",
      className
    )}
    {...props}
  >
    {children}
  </div>
);

const CardHeader = ({ children, className, ...props }) => (
  <div className={cn("px-6 py-4 border-b border-gray-200", className)} {...props}>
    {children}
  </div>
);

const CardContent = ({ children, className, ...props }) => (
  <div className={cn("px-6 py-4", className)} {...props}>
    {children}
  </div>
);
```

### 5.4 Animation Library

#### Transition Presets
```css
/* Smooth transitions */
.transition-smooth {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.transition-bounce {
  transition: all 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

/* Entrance animations */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.animate-scale-in {
  animation: scaleIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
```

#### Framer Motion Presets
```tsx
export const fadeInUpVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] }
  }
};

export const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1
    }
  }
};

export const slideInVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: { duration: 0.4, ease: "easeOut" }
  }
};
```

## 6. Progressive Web App (PWA) Features

### 6.1 PWA Configuration

#### Manifest Configuration
```json
{
  "name": "AIWFE - AI Workflow Engine",
  "short_name": "AIWFE",
  "description": "AI-powered workflow automation and productivity platform",
  "start_url": "/dashboard",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#2563eb",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    }
  ],
  "categories": ["productivity", "business", "utilities"],
  "shortcuts": [
    {
      "name": "Dashboard",
      "short_name": "Dashboard",
      "description": "View your dashboard",
      "url": "/dashboard",
      "icons": [{ "src": "/icons/dashboard.png", "sizes": "96x96" }]
    },
    {
      "name": "New Chat",
      "short_name": "Chat",
      "description": "Start a new AI chat",
      "url": "/chat/new",
      "icons": [{ "src": "/icons/chat.png", "sizes": "96x96" }]
    }
  ]
}
```

#### Service Worker Features
```typescript
// Offline functionality
const CACHE_NAME = 'aiwfe-v1';
const STATIC_ASSETS = [
  '/',
  '/dashboard',
  '/offline',
  '/manifest.json'
];

// Cache strategies
const cacheStrategies = {
  static: 'CacheFirst',
  api: 'NetworkFirst',
  images: 'CacheFirst'
};

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    event.waitUntil(syncOfflineActions());
  }
});

// Push notifications
self.addEventListener('push', (event) => {
  const options = {
    body: event.data.text(),
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge.png',
    actions: [
      { action: 'view', title: 'View' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('AIWFE Notification', options)
  );
});
```

### 6.2 Offline Functionality

#### Offline Pages
```tsx
const OfflinePage = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center p-8">
      <div className="w-24 h-24 mx-auto mb-6 text-gray-400">
        <WifiOffIcon />
      </div>
      <h1 className="text-2xl font-semibold mb-4">You're offline</h1>
      <p className="text-gray-600 mb-6">
        Some features may be limited while offline. 
        We'll sync your changes when you're back online.
      </p>
      <Button onClick={() => window.location.reload()}>
        Try Again
      </Button>
    </div>
  </div>
);
```

#### Offline Data Management
```typescript
// Offline queue for actions
class OfflineQueue {
  private queue: OfflineAction[] = [];
  
  async addAction(action: OfflineAction) {
    this.queue.push(action);
    await this.saveToStorage();
    
    if (navigator.onLine) {
      this.processQueue();
    }
  }
  
  async processQueue() {
    while (this.queue.length > 0) {
      const action = this.queue.shift();
      try {
        await this.executeAction(action);
      } catch (error) {
        this.queue.unshift(action);
        break;
      }
    }
    await this.saveToStorage();
  }
}
```

## 7. Accessibility Implementation

### 7.1 WCAG 2.1 AA Compliance

#### Accessibility Features
```tsx
// Screen reader support
const AccessibleButton = ({ children, ...props }) => (
  <button
    role="button"
    aria-label={props['aria-label']}
    aria-describedby={props['aria-describedby']}
    tabIndex={0}
    {...props}
  >
    {children}
  </button>
);

// Keyboard navigation
const useKeyboardNavigation = () => {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.key) {
        case 'Escape':
          closeModal();
          break;
        case 'Tab':
          handleTabNavigation(event);
          break;
        case 'Enter':
        case ' ':
          if (event.target instanceof HTMLButtonElement) {
            event.target.click();
          }
          break;
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);
};

// Focus management
const FocusTrap = ({ children, active }) => {
  const containerRef = useRef(null);
  
  useEffect(() => {
    if (active && containerRef.current) {
      const focusableElements = containerRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      
      if (focusableElements.length > 0) {
        focusableElements[0].focus();
      }
    }
  }, [active]);
  
  return <div ref={containerRef}>{children}</div>;
};
```

#### Color Contrast and Visual Design
```css
/* High contrast mode support */
@media (prefers-contrast: high) {
  :root {
    --text-primary: #000000;
    --text-secondary: #333333;
    --border-color: #000000;
    --background-elevated: #ffffff;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Focus indicators */
.focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

/* High contrast focus indicators */
@media (prefers-contrast: high) {
  .focus-visible {
    outline: 3px solid #000000;
    outline-offset: 3px;
  }
}
```

### 7.2 Screen Reader Support

#### ARIA Implementation
```tsx
const NavigationMenu = () => (
  <nav role="navigation" aria-label="Main navigation">
    <ul role="menubar">
      {menuItems.map((item) => (
        <li key={item.id} role="none">
          <Link
            href={item.href}
            role="menuitem"
            aria-current={pathname === item.href ? 'page' : undefined}
            className="nav-link"
          >
            {item.label}
          </Link>
        </li>
      ))}
    </ul>
  </nav>
);

const TaskCard = ({ task }) => (
  <article
    role="article"
    aria-labelledby={`task-title-${task.id}`}
    aria-describedby={`task-description-${task.id}`}
  >
    <h3 id={`task-title-${task.id}`}>{task.title}</h3>
    <p id={`task-description-${task.id}`}>{task.description}</p>
    <div role="group" aria-label="Task actions">
      <Button aria-label={`Edit ${task.title}`}>Edit</Button>
      <Button aria-label={`Delete ${task.title}`}>Delete</Button>
    </div>
  </article>
);
```

## 8. Performance Optimization

### 8.1 Code Splitting and Lazy Loading

#### Route-based Code Splitting
```tsx
// Lazy load pages
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Opportunities = lazy(() => import('./pages/Opportunities'));
const Calendar = lazy(() => import('./pages/Calendar'));
const Chat = lazy(() => import('./pages/Chat'));

// Component-based code splitting
const LazyComponent = lazy(() => 
  import('./components/HeavyComponent').then(module => ({
    default: module.HeavyComponent
  }))
);

// Conditional loading based on features
const ConditionalComponent = lazy(() => {
  if (featureFlags.advancedFeatures) {
    return import('./components/AdvancedComponent');
  }
  return import('./components/BasicComponent');
});
```

#### Image Optimization
```tsx
import Image from 'next/image';

const OptimizedImage = ({ src, alt, ...props }) => (
  <Image
    src={src}
    alt={alt}
    priority={props.priority}
    placeholder="blur"
    blurDataURL="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD..."
    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
    {...props}
  />
);
```

### 8.2 Bundle Optimization

#### Webpack Bundle Analysis
```typescript
// next.config.js
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true'
});

module.exports = withBundleAnalyzer({
  experimental: {
    optimizeCss: true,
    optimizeImages: true
  },
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production'
  },
  swcMinify: true
});
```

#### Tree Shaking Configuration
```typescript
// Import only needed utilities
import { cn } from '@/lib/utils';
import { format } from 'date-fns/format';
import { addDays } from 'date-fns/addDays';

// Avoid importing entire libraries
// ❌ Bad
import * as _ from 'lodash';

// ✅ Good  
import debounce from 'lodash/debounce';
import throttle from 'lodash/throttle';
```

## 9. Testing Strategy

### 9.1 Component Testing

#### React Testing Library Examples
```tsx
// Button Component Test
describe('Button Component', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });
  
  it('handles click events', async () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    await user.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
  
  it('applies correct CSS classes', () => {
    render(<Button variant="secondary">Button</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-white');
  });
});

// Form Component Test
describe('TaskForm Component', () => {
  it('submits form with correct data', async () => {
    const handleSubmit = jest.fn();
    render(<TaskForm onSubmit={handleSubmit} />);
    
    await user.type(screen.getByLabelText(/title/i), 'New Task');
    await user.type(screen.getByLabelText(/description/i), 'Task description');
    await user.click(screen.getByRole('button', { name: /submit/i }));
    
    expect(handleSubmit).toHaveBeenCalledWith({
      title: 'New Task',
      description: 'Task description'
    });
  });
});
```

### 9.2 End-to-End Testing

#### Playwright Test Examples
```typescript
// E2E test for login flow
test('user can log in successfully', async ({ page }) => {
  await page.goto('/login');
  
  await page.fill('[data-testid="email"]', 'user@example.com');
  await page.fill('[data-testid="password"]', 'password123');
  await page.click('[data-testid="login-button"]');
  
  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('[data-testid="user-name"]')).toBeVisible();
});

// E2E test for task creation
test('user can create a new task', async ({ page }) => {
  await page.goto('/opportunities');
  
  await page.click('[data-testid="add-task-button"]');
  await page.fill('[data-testid="task-title"]', 'Test Task');
  await page.fill('[data-testid="task-description"]', 'Test Description');
  await page.click('[data-testid="save-task-button"]');
  
  await expect(page.locator('text=Test Task')).toBeVisible();
});

// Performance testing
test('dashboard loads within performance budget', async ({ page }) => {
  const startTime = Date.now();
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');
  const loadTime = Date.now() - startTime;
  
  expect(loadTime).toBeLessThan(3000); // 3 second budget
});
```

### 9.3 Accessibility Testing

#### Automated Accessibility Tests
```typescript
import { axe, toHaveNoViolations } from 'jest-axe';
import { render } from '@testing-library/react';

expect.extend(toHaveNoViolations);

describe('Accessibility Tests', () => {
  it('should not have any accessibility violations', async () => {
    const { container } = render(<Dashboard />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
  
  it('should have proper focus management', async () => {
    render(<Modal />);
    const modal = screen.getByRole('dialog');
    expect(modal).toHaveFocus();
  });
  
  it('should have proper ARIA labels', () => {
    render(<TaskCard task={mockTask} />);
    expect(screen.getByRole('article')).toHaveAttribute('aria-labelledby');
  });
});
```

## 10. Deployment and Build Process

### 10.1 Build Configuration

#### Next.js Configuration
```typescript
// next.config.js
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: ['localhost', 'api.aiwfe.com'],
    formats: ['image/webp', 'image/avif']
  },
  experimental: {
    appDir: true,
    typedRoutes: true
  },
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_BASE_URL}/:path*`
      }
    ];
  }
};

module.exports = nextConfig;
```

#### Docker Configuration
```dockerfile
# Dockerfile for WebUI
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --only=production

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT 3000

CMD ["node", "server.js"]
```

### 10.2 Kubernetes Deployment

#### Kubernetes Manifests
```yaml
# webui-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiwfe-webui
  namespace: aiwfe-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aiwfe-webui
  template:
    metadata:
      labels:
        app: aiwfe-webui
    spec:
      containers:
      - name: webui
        image: aiwfe/webui:latest
        ports:
        - containerPort: 3000
        env:
        - name: API_BASE_URL
          value: "http://api-gateway:8080"
        - name: NODE_ENV
          value: "production"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: aiwfe-webui-service
  namespace: aiwfe-system
spec:
  selector:
    app: aiwfe-webui
  ports:
  - port: 80
    targetPort: 3000
  type: ClusterIP

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aiwfe-webui-hpa
  namespace: aiwfe-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aiwfe-webui
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 11. Migration Strategy from Svelte Implementation

### 11.1 Migration Planning and Data Preservation

#### Current State Analysis
```yaml
Existing Svelte Implementation:
  Framework: SvelteKit with TypeScript
  State Management: Svelte stores
  Styling: Tailwind CSS with custom components
  Authentication: Custom JWT implementation
  API Integration: Fetch-based client
  Data Storage: Local storage for preferences
  
Key Features to Preserve:
  - User authentication and session management
  - Existing task data and user preferences
  - Chat history and conversation threads
  - Calendar integrations and sync status
  - Custom themes and UI preferences
```

#### Migration Phases

**Phase 1: Parallel Development Setup (Week 1-2)**
```yaml
Infrastructure:
  - Set up Next.js project alongside existing Svelte app
  - Configure shared API endpoints for both applications
  - Implement feature flagging system for gradual rollout
  - Set up database migrations for new schema requirements

Data Migration:
  - Create data export utilities from Svelte app
  - Design migration scripts for user data transfer
  - Implement backup and rollback procedures
  - Test data integrity across migrations
```

**Phase 2: Feature Parity Development (Week 3-8)**
```yaml
Core Features Migration:
  - Authentication system with session preservation
  - Dashboard functionality with data continuity
  - Task management with existing data import
  - Chat interface with conversation history
  - Calendar integration with existing connections

User Experience Continuity:
  - Import user preferences and themes
  - Preserve keyboard shortcuts and workflows
  - Maintain familiar navigation patterns
  - Ensure seamless data access
```

**Phase 3: Progressive Rollout (Week 9-10)**
```yaml
Rollout Strategy:
  - Beta release to internal users for testing
  - Gradual rollout to 10% of user base
  - Monitor performance and gather feedback
  - Address issues and optimize based on usage

Fallback Mechanisms:
  - Ability to revert to Svelte app if needed
  - Data synchronization between both versions
  - User preference for version selection
  - Monitoring and alerting for migration issues
```

### 11.2 Data Migration Specifications

#### User Data Migration
```typescript
// Migration Utility Types
interface MigrationData {
  user: UserProfile;
  tasks: Task[];
  conversations: ChatConversation[];
  preferences: UserPreferences;
  calendarConnections: CalendarIntegration[];
}

// Migration Service
class DataMigrationService {
  async exportSvelteData(userId: string): Promise<MigrationData> {
    // Export from Svelte app's local storage and API
    return {
      user: await this.exportUserProfile(userId),
      tasks: await this.exportTasks(userId),
      conversations: await this.exportConversations(userId),
      preferences: await this.exportPreferences(userId),
      calendarConnections: await this.exportCalendarData(userId)
    };
  }

  async importToNextApp(data: MigrationData): Promise<void> {
    // Import into Next.js app with validation
    await this.validateMigrationData(data);
    await this.importUserProfile(data.user);
    await this.importTasks(data.tasks);
    await this.importConversations(data.conversations);
    await this.importPreferences(data.preferences);
    await this.importCalendarConnections(data.calendarConnections);
  }

  async validateMigrationData(data: MigrationData): Promise<boolean> {
    // Comprehensive validation of migrated data
    // Ensure data integrity and format compatibility
    // Return validation report with any issues
  }
}
```

#### API Compatibility Layer
```typescript
// Backward Compatibility Adapter
class APICompatibilityLayer {
  async handleSvelteRequest(request: SvelteAPIRequest): Promise<NextAPIResponse> {
    // Transform Svelte API calls to Next.js format
    const transformedRequest = this.transformRequest(request);
    const response = await this.processRequest(transformedRequest);
    return this.transformResponse(response);
  }

  private transformRequest(svelteRequest: SvelteAPIRequest): NextAPIRequest {
    // Convert Svelte-specific request format to Next.js
    // Handle authentication token transformation
    // Maintain request ID for tracking
  }
}
```

### 11.3 Rollback and Recovery Procedures

#### Emergency Rollback Plan
```yaml
Rollback Triggers:
  - Performance degradation > 50%
  - Error rate > 5%
  - User satisfaction score < 7/10
  - Critical feature failures

Rollback Process:
  1. Immediate DNS switch back to Svelte app
  2. Data synchronization from Next.js back to Svelte
  3. User notification of temporary reversion
  4. Issue investigation and resolution timeline

Data Preservation:
  - Real-time backup of all user actions
  - Incremental data sync between versions
  - Point-in-time recovery capabilities
  - No data loss guarantee during migration
```

## 12. Runtime Performance Monitoring

### 12.1 Core Web Vitals Tracking

#### Real-time Performance Monitoring
```typescript
// Performance Monitoring Service
class PerformanceMonitor {
  private observer: PerformanceObserver | null = null;
  private metrics: Map<string, number[]> = new Map();

  init() {
    // Core Web Vitals monitoring
    this.trackLCP(); // Largest Contentful Paint
    this.trackFID(); // First Input Delay
    this.trackCLS(); // Cumulative Layout Shift
    this.trackFCP(); // First Contentful Paint
    this.trackTTFB(); // Time to First Byte
  }

  private trackLCP() {
    new PerformanceObserver((entryList) => {
      const entries = entryList.getEntries();
      const lastEntry = entries[entries.length - 1];
      this.recordMetric('LCP', lastEntry.startTime);
    }).observe({ entryTypes: ['largest-contentful-paint'] });
  }

  private trackFID() {
    new PerformanceObserver((entryList) => {
      const entries = entryList.getEntries();
      entries.forEach((entry) => {
        this.recordMetric('FID', entry.processingStart - entry.startTime);
      });
    }).observe({ entryTypes: ['first-input'] });
  }

  private trackCLS() {
    let clsValue = 0;
    new PerformanceObserver((entryList) => {
      const entries = entryList.getEntries();
      entries.forEach((entry) => {
        if (!entry.hadRecentInput) {
          clsValue += entry.value;
          this.recordMetric('CLS', clsValue);
        }
      });
    }).observe({ entryTypes: ['layout-shift'] });
  }

  private recordMetric(name: string, value: number) {
    if (!this.metrics.has(name)) {
      this.metrics.set(name, []);
    }
    this.metrics.get(name)!.push(value);
    
    // Send to analytics
    this.sendToAnalytics(name, value);
  }

  private sendToAnalytics(metric: string, value: number) {
    // Google Analytics 4
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('event', 'performance_metric', {
        metric_name: metric,
        value: Math.round(value),
        page_path: window.location.pathname
      });
    }

    // Custom monitoring endpoint
    fetch('/api/metrics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        metric,
        value,
        timestamp: Date.now(),
        url: window.location.href,
        userAgent: navigator.userAgent
      })
    }).catch(console.error);
  }
}
```

#### User Interaction Metrics
```typescript
// User Experience Tracking
class UXMetrics {
  private interactions: InteractionMetric[] = [];

  init() {
    this.trackPageTransitions();
    this.trackFormInteractions();
    this.trackErrorRates();
    this.trackFeatureUsage();
  }

  private trackPageTransitions() {
    // Track navigation performance
    const navigationObserver = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        if (entry.entryType === 'navigation') {
          this.recordInteraction('page_transition', {
            duration: entry.loadEventEnd - entry.startTime,
            page: window.location.pathname
          });
        }
      });
    });
    navigationObserver.observe({ entryTypes: ['navigation'] });
  }

  private trackFormInteractions() {
    document.addEventListener('submit', (event) => {
      const form = event.target as HTMLFormElement;
      const formId = form.id || form.className;
      
      this.recordInteraction('form_submission', {
        form: formId,
        success: true // Will be updated based on response
      });
    });
  }

  private trackErrorRates() {
    window.addEventListener('error', (event) => {
      this.recordInteraction('javascript_error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        stack: event.error?.stack
      });
    });

    window.addEventListener('unhandledrejection', (event) => {
      this.recordInteraction('promise_rejection', {
        reason: event.reason?.toString()
      });
    });
  }

  private trackFeatureUsage() {
    // Track usage of key features
    const features = ['chat', 'tasks', 'calendar', 'opportunities'];
    
    features.forEach(feature => {
      document.addEventListener('click', (event) => {
        const target = event.target as Element;
        if (target.closest(`[data-feature="${feature}"]`)) {
          this.recordInteraction('feature_usage', {
            feature,
            timestamp: Date.now()
          });
        }
      });
    });
  }

  private recordInteraction(type: string, data: any) {
    this.interactions.push({
      type,
      data,
      timestamp: Date.now(),
      sessionId: this.getSessionId()
    });

    // Batch send to analytics
    if (this.interactions.length >= 10) {
      this.flushInteractions();
    }
  }

  private flushInteractions() {
    if (this.interactions.length === 0) return;

    fetch('/api/ux-metrics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.interactions)
    }).catch(console.error);

    this.interactions = [];
  }
}
```

### 12.2 Custom Performance Dashboards

#### Monitoring Dashboard Configuration
```yaml
Performance Metrics Dashboard:
  Core Web Vitals:
    - LCP (Target: < 2.5s)
    - FID (Target: < 100ms)
    - CLS (Target: < 0.1)
    - FCP (Target: < 1.8s)
    - TTFB (Target: < 600ms)

  Application Metrics:
    - Page Load Times by Route
    - API Response Times
    - WebSocket Connection Health
    - Bundle Size Tracking
    - Memory Usage Patterns

  User Experience Metrics:
    - Task Completion Rates
    - Error Recovery Success
    - Feature Adoption Rates
    - Session Duration
    - User Satisfaction Scores

  Business Metrics:
    - Daily/Monthly Active Users
    - Feature Usage Statistics
    - Conversion Funnel Performance
    - Retention Rates
```

#### Alerting and Monitoring Rules
```typescript
// Performance Alerting System
interface AlertRule {
  metric: string;
  threshold: number;
  operator: 'gt' | 'lt' | 'eq';
  duration: number; // minutes
  severity: 'low' | 'medium' | 'high' | 'critical';
}

const performanceAlerts: AlertRule[] = [
  // Critical performance issues
  {
    metric: 'LCP',
    threshold: 4000, // 4 seconds
    operator: 'gt',
    duration: 5,
    severity: 'critical'
  },
  {
    metric: 'error_rate',
    threshold: 5, // 5%
    operator: 'gt',
    duration: 2,
    severity: 'high'
  },
  {
    metric: 'api_response_time',
    threshold: 2000, // 2 seconds
    operator: 'gt',
    duration: 3,
    severity: 'medium'
  },
  // User experience degradation
  {
    metric: 'task_completion_rate',
    threshold: 85, // 85%
    operator: 'lt',
    duration: 10,
    severity: 'medium'
  }
];

class PerformanceAlerting {
  private checkAlerts() {
    performanceAlerts.forEach(rule => {
      this.evaluateRule(rule);
    });
  }

  private async evaluateRule(rule: AlertRule) {
    const recentValues = await this.getRecentMetrics(
      rule.metric, 
      rule.duration
    );
    
    const shouldAlert = recentValues.every(value => 
      this.compareValue(value, rule.threshold, rule.operator)
    );

    if (shouldAlert) {
      this.triggerAlert(rule, recentValues);
    }
  }

  private triggerAlert(rule: AlertRule, values: number[]) {
    // Send to monitoring service (PagerDuty, Slack, etc.)
    const alert = {
      metric: rule.metric,
      severity: rule.severity,
      values,
      timestamp: Date.now(),
      message: `${rule.metric} has been ${rule.operator} ${rule.threshold} for ${rule.duration} minutes`
    };

    // Implementation depends on monitoring infrastructure
    this.sendAlert(alert);
  }
}
```

### 12.3 A/B Testing and Performance Optimization

#### Feature Flag Performance Testing
```typescript
// A/B Testing for Performance Features
interface PerformanceExperiment {
  name: string;
  variants: {
    control: PerformanceConfig;
    treatment: PerformanceConfig;
  };
  metrics: string[];
  trafficSplit: number; // 0-100
}

const performanceExperiments: PerformanceExperiment[] = [
  {
    name: 'lazy_loading_strategy',
    variants: {
      control: { 
        lazyLoadThreshold: '300px',
        preloadCritical: false 
      },
      treatment: { 
        lazyLoadThreshold: '500px',
        preloadCritical: true 
      }
    },
    metrics: ['LCP', 'FCP', 'bundle_size'],
    trafficSplit: 20
  },
  {
    name: 'animation_performance',
    variants: {
      control: { 
        animationFramework: 'css',
        reducedMotion: false 
      },
      treatment: { 
        animationFramework: 'framer-motion',
        reducedMotion: 'auto' 
      }
    },
    metrics: ['FID', 'CLS', 'memory_usage'],
    trafficSplit: 15
  }
];
```

## 13. Implementation Timeline

### 13.1 Development Phases

#### Phase 1: Foundation Setup (Weeks 1-2)
```yaml
Week 1:
  - Next.js project setup with TypeScript
  - Tailwind CSS configuration
  - Basic component library
  - Design system implementation
  - PWA configuration

Week 2:
  - Authentication implementation
  - API client setup
  - Basic routing structure
  - Testing framework setup
  - CI/CD pipeline configuration
```

#### Phase 2: Core Pages (Weeks 3-6)
```yaml
Week 3:
  - Landing page implementation
  - Basic navigation system
  - Login/register pages
  - Error and loading states

Week 4:
  - Dashboard page layout
  - Task components
  - Statistics widgets
  - Real-time updates setup

Week 5:
  - Opportunities page (Kanban board)
  - Drag and drop functionality
  - Task creation and editing
  - Filtering and search

Week 6:
  - Calendar integration
  - Google Calendar sync
  - Event management
  - Calendar view components
```

#### Phase 3: Advanced Features (Weeks 7-10)
```yaml
Week 7:
  - Chat interface implementation
  - AIWFE API integration
  - Message components
  - Real-time messaging

Week 8:
  - Pieces integration setup
  - Context synchronization
  - Developer tools integration
  - Code snippet management

Week 9:
  - Settings and preferences
  - User profile management
  - Theme customization
  - Notification settings

Week 10:
  - Performance optimization
  - Bundle size reduction
  - Caching implementation
  - SEO optimization
```

#### Phase 4: Testing and Polish (Weeks 11-12)
```yaml
Week 11:
  - Comprehensive testing
  - Bug fixes and optimization
  - Accessibility audit
  - Performance testing

Week 12:
  - Final integration testing
  - Documentation completion
  - Production deployment
  - User training materials
```

## 14. Success Metrics and Validation

### 14.1 Technical Metrics

#### Performance Benchmarks
```yaml
Page Load Performance:
  - Landing page: < 1.5 seconds
  - Dashboard: < 2 seconds
  - Opportunities: < 2.5 seconds
  - Calendar: < 2 seconds

Bundle Size Targets:
  - Initial bundle: < 200KB gzipped
  - Total JavaScript: < 500KB gzipped
  - CSS bundle: < 50KB gzipped

Lighthouse Scores:
  - Performance: > 90
  - Accessibility: > 95
  - Best Practices: > 90
  - SEO: > 90
```

#### Code Quality Metrics
```yaml
Test Coverage:
  - Unit tests: > 80%
  - Integration tests: > 70%
  - E2E tests: > 60%

Code Quality:
  - TypeScript coverage: 100%
  - ESLint violations: 0
  - Prettier formatting: 100%
  - Security vulnerabilities: 0 critical
```

### 14.2 User Experience Metrics

#### Usability Benchmarks
```yaml
User Satisfaction:
  - System Usability Scale (SUS): > 80
  - Net Promoter Score (NPS): > 7
  - Task completion rate: > 95%
  - Error recovery rate: > 90%

Accessibility Compliance:
  - WCAG 2.1 AA: 100% compliance
  - Screen reader compatibility: Full support
  - Keyboard navigation: Complete coverage
  - Color contrast: AAA rating where possible
```

## 15. Approval and Next Steps

### 15.1 Design Review Checklist

- [ ] Wireframe requirements fully addressed
- [ ] Cosmos.so aesthetic inspiration correctly implemented
- [ ] Micro.so functionality patterns integrated
- [ ] Accessibility standards met (WCAG 2.1 AA)
- [ ] Performance targets achievable
- [ ] PWA features properly specified
- [ ] Testing strategy comprehensive
- [ ] Deployment plan viable

### 15.2 Technical Review Checklist

- [ ] Technology stack approved by engineering team
- [ ] API integration patterns validated
- [ ] State management approach confirmed
- [ ] Build and deployment process reviewed
- [ ] Security considerations addressed
- [ ] Performance optimization strategies approved
- [ ] Monitoring and analytics plan confirmed

**Design Lead Approval**: _____________________ Date: _______

**Frontend Architect Approval**: _____________________ Date: _______

**UX Lead Approval**: _____________________ Date: _______

**Technical Lead Approval**: _____________________ Date: _______

---

*This WebUI redesign specification provides a comprehensive blueprint for transforming the AIWFE interface into a modern, accessible, and highly performant Progressive Web Application that embodies the best of contemporary design and functionality patterns while serving the specific needs of the AI Workflow Engine platform.*