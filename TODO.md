# Vashandi Workers App - Outstanding Features TODO

## Overview
This document outlines all remaining features and fixes needed to finalize the Vashandi Workers App from MVP to production-ready status.

---

## 1. MESSAGING SYSTEM (CRITICAL - HIGH PRIORITY)

### 1.1 Fix 403 Forbidden Errors on Message POST
- **Issue**: Users getting 403 when trying to send messages via `/api/messages/`
- **Root Cause**: Likely CSRF token not being passed correctly or user permission issues
- **Tasks**:
  - [x] Debug CSRF token extraction and validation in messaging.js
  - [x] Verify CSRF token is being sent in POST headers
  - [x] Check MessageViewSet permissions (currently `permissions.IsAuthenticated`)
  - [x] Add detailed error logging to backend to show exact reason for 403
  - [x] Test with authenticated user to ensure sender is set correctly
  - [x] Add user-friendly error messages explaining:
    - "You must be logged in to send messages"
    - "CSRF token expired, please refresh the page"
    - "You don't have permission to send this message"
    - "Recipient user not found"

### 1.2 Message History Display
- **Current State**: Modal loads and displays messages (if they exist)
- **Tasks**:
  - [x] Fix message loading to show conversation history when modal opens
  - [x] Sort messages chronologically (oldest first in conversation view)
  - [x] Add visual distinction between sent/received messages (left/right alignment)
  - [x] Display sender names and timestamps for each message
  - [x] Add "No messages yet" placeholder when conversation is empty
  - [x] Auto-scroll to latest message when new message is sent
  - [x] Implement message read receipt (mark as read when recipient views)

### 1.3 Real-time Message Updates
- **Current State**: Manual page refresh needed to see new messages
- **Tasks**:
  - [x] Implement auto-refresh of messages every 5 seconds while modal is open
  - [x] Add visual indicator when new message arrives ("New message from X")
  - [x] Play notification sound/toast when message received (optional)
  - [x] Update unread message count in real-time

---

## 2. INBOX & MESSAGE COUNTER (HIGH PRIORITY)

### 2.1 Inbox Page/View
- **Current State**: No dedicated inbox page
- **Tasks**:
  - [x] Create `/inbox/` or `/messages/` page in dashboard
  - [x] Show list of all conversations grouped by user
  - [x] Display latest message preview in conversation list
  - [x] Show timestamp of last message
  - [x] Highlight unread conversations (bold/colored)
  - [x] Sort by most recent first
  - [x] Click conversation to open full thread
  - [x] Add search functionality to find conversations by user name

### 2.2 Unread Message Counter
- **Current State**: No counter displayed
- **Tasks**:
  - [x] Add unread count badge to navigation bar (e.g., "Messages (3)")
  - [x] Create API endpoint `/api/messages/unread-count/` that returns count
  - [x] Fetch unread count on dashboard load
  - [x] Update counter in real-time (every 10 seconds)
  - [x] Show "You have X unread messages" when counter > 0
  - [x] Clear counter when user opens inbox
  - [x] Add red badge styling to draw attention

### 2.3 Message Notifications
- **Current State**: Silent (no notifications)
- **Tasks**:
  - [x] Create notification toast/banner at top of page for new messages
  - [x] Show: "New message from [Name]: [Preview]"
  - [x] Auto-dismiss after 5 seconds
  - [x] Add click handler to open conversation
  - [x] Add notification sound (optional, user preference)

---

## 3. JOB MANAGEMENT (HIGH PRIORITY)

### 3.1 Job Status Management
- **Current State**: Jobs have status field but no UI to update it
- **Tasks**:
  - [x] Create job detail modal/page showing full job info
  - [x] Add status change functionality for job owner (client)
  - [x] Status flow: Open → In Progress → Completed (or Cancelled)
  - [x] Add visual status indicators (color badges):
    - Open: 🟢 Green
    - In Progress: 🔵 Blue
    - Completed: ⚫ Gray
    - Cancelled: 🔴 Red
  - [x] Restrict status changes to job owner only
  - [x] Add confirmation dialog before status change
  - [x] Add notes/reason when changing status (especially for cancellation)
  - [x] Send notification to assigned provider when status changes

### 3.2 Job Listing & Filtering (Provider View)
- **Current State**: Jobs displayed as cards but limited filtering
- **Tasks**:
  - [x] Improve job filtering by:
    - [x] Category (already working)
    - [x] Status (open/in progress/completed/cancelled)
    - [x] Budget range (min/max)
    - [x] Location (current location preferences)
    - [x] Date posted (last 7 days, 30 days, all)
    - [x] Deadline (urgent, this week, this month, future)
  - [x] Add sort options:
    - [x] Newest first (current default)
    - [x] Highest budget first
    - [x] Closest deadline first
    - [x] Most relevant (based on provider's services)
  - [x] Show job posting age ("Posted 2 days ago")
  - [x] Add "Saved Jobs" / "Favorite" functionality

### 3.3 Job Details View
- **Current State**: Minimal details shown in card
- **Tasks**:
  - [x] Create full job detail page/modal with:
    - [x] Full description with proper formatting
    - [x] Client information (name, rating, reviews, contact button)
    - [x] Budget breakdown (total, per hour estimate, payment terms)
    - [x] Location with map (if available)
    - [x] Deadline and urgency indicator
    - [x] Required skills/categories
    - [x] Previous reviews/work samples (if any)
    - [x] Number of bids received (for client view)
    - [x] Current assigned provider (if any)
  - [x] Add "Apply for Job" / "Place Bid" button (see Bidding section)

---

## 4. BIDDING PROCESS (HIGH PRIORITY)

### 4.1 Create Bid Model & API
- **Current State**: No bidding system exists
- **Tasks**:
  - [x] Create `Bid` model in models.py with fields:
    - provider (FK to User)
    - job (FK to Job)
    - amount (DecimalField for bid amount)
    - proposal_message (TextField for provider's proposal)
    - timeline (CharField: "ASAP", "1 week", "2 weeks", etc.)
    - is_accepted (BooleanField)
    - created_at (DateTimeField)
    - updated_at (DateTimeField)
  - [x] Create BidSerializer
  - [x] Create BidViewSet with endpoints:
    - POST `/api/bids/` - Create bid
    - GET `/api/bids/?job={id}` - List bids for a job
    - GET `/api/bids/?provider={id}` - List bids by provider
    - PATCH `/api/bids/{id}/` - Update bid (accept/reject)
  - [x] Add permission checks:
    - Only providers can create bids
    - Only job owner can accept/reject bids
    - Can't bid on own jobs
    - Can't place multiple bids on same job

### 4.2 Bidding UI - Provider Side
- **Current State**: "Bid Now" button is placeholder
- **Tasks**:
  - [x] Create "Place Bid" modal form with fields:
    - [x] Bid amount (currency input)
    - [x] Timeline/Delivery date (dropdown or date picker)
    - [x] Proposal message (textarea - "Why should they hire you?")
    - [x] Attach work samples/portfolio links (optional)
  - [x] Validate:
    - [x] Bid amount > 0
    - [x] Timeline is realistic
    - [x] Proposal is at least 50 characters
  - [x] Submit bid via API
  - [x] Show success message: "Bid placed! Wait for response from client"
  - [x] Allow editing own bid before client accepts
  - [x] Show "Bid pending" status on card if bid already placed
  - [x] Allow withdrawing bid with confirmation

### 4.3 Bidding UI - Client Side
- **Current State**: No way to view or accept bids
- **Tasks**:
  - [x] Create "Bids" tab/section in job detail view
  - [x] Display list of all bids for the job with:
    - [x] Provider name, avatar, rating
    - [x] Bid amount
    - [x] Proposed timeline
    - [x] Provider's proposal message
    - [x] Provider's recent reviews (last 3)
    - [x] "Accept Bid" and "Reject Bid" buttons
  - [x] Sort bids by:
    - [x] Lowest price first
    - [x] Highest rated provider first
    - [x] Newest bid first
  - [x] Show "No bids yet" message if no bids
  - [x] Once bid accepted:
    - [x] Mark job as "In Progress"
    - [x] Reject all other bids automatically
    - [x] Notify assigned provider via message

---

## 5. USER AUTHENTICATION & PROFILE (MEDIUM PRIORITY)

### 5.1 Login Error Handling
- **Current State**: Generic error messages
- **Tasks**:
  - [x] Show specific errors:
    - [x] "Email not found" (if email doesn't exist)
    - [x] "Password incorrect" (if password wrong)
    - [x] "Account disabled" (if user inactive)
  - [x] Add "Forgot Password" link
  - [x] Add account recovery flow (email verification)

### 5.2 User Profile Page
- **Current State**: No profile editing
- **Tasks**:
  - [x] Create `/profile/` page showing:
    - [x] User info (name, email, phone, location, bio)
    - [x] Avatar/initials
    - [x] Role (client/provider/both)
    - [x] Member since date
    - [x] Stats (jobs posted, jobs completed, services listed, ratings)
  - [x] Add "Edit Profile" functionality:
    - [x] Edit name, phone, location, bio
    - [x] Upload custom avatar (replace initials)
    - [x] Change password
    - [x] Link social profiles
  - [x] For providers, show:
    - [x] All services they offer
    - [x] Total reviews and average rating
    - [x] Number of completed jobs
    - [x] Response time/success rate

### 5.3 User Role Management
- **Current State**: Toggle between roles works
- **Tasks**:
  - [x] Show current active role clearly in nav/dashboard
  - [x] Prevent same user from being both provider and client in same transaction
  - [x] Add role-specific views (already partially done)
  - [x] Show "Switch to Provider/Client mode" button prominently

---

## 6. REVIEWS & RATINGS (MEDIUM PRIORITY)

### 6.1 Review System
- **Current State**: Review model exists but no UI to leave/view reviews
- **Tasks**:
  - [x] Create review submission form after job completion:
    - [x] Star rating (1-5) with visual feedback
    - [x] Written review (optional)
    - [x] Review prompt: "How was the work quality?"
  - [x] Prevent reviewing own work
  - [x] Prevent duplicate reviews for same job
  - [x] Allow editing review within 30 days of posting
  - [x] Allow deleting own review with confirmation

### 6.2 Review Display
- **Current State**: No review display on provider profiles
- **Tasks**:
  - [x] Show all reviews on provider service card/profile:
    - [x] Overall rating (e.g., 4.8 out of 5)
    - [x] Number of reviews
    - [x] List of recent reviews with:
      - [x] Star rating
      - [x] Review text
      - [x] Reviewer name and date
      - [x] Photos/attachments if any
  - [x] Sort reviews by:
    - [x] Most recent first
    - [x] Most helpful first (upvote system)
  - [x] Show review statistics:
    - [x] Distribution by rating (bar chart)
    - [x] Percentage of positive reviews

---

## 7. NOTIFICATIONS & ALERTS (MEDIUM PRIORITY)

### 7.1 System Notifications
- **Current State**: No notification system
- **Tasks**:
  - [x] Create `Notification` model with fields:
    - notification_type (enum: message, bid, status_change, review, etc.)
    - recipient (FK to User)
    - actor (FK to User - who caused notification)
    - title (CharField)
    - description (TextField)
    - related_object_id (GenericFK to any model)
    - is_read (BooleanField)
    - created_at (DateTimeField)
  - [x] Create NotificationViewSet with endpoints:
    - GET `/api/notifications/` - list user's notifications
    - PATCH `/api/notifications/{id}/mark-read/` - mark as read
    - DELETE `/api/notifications/{id}/` - delete notification
  - [x] Create notification triggers for:
    - [x] New message received
    - [x] New bid on job
    - [x] Bid accepted/rejected
    - [x] Job status changed
    - [x] New review posted
    - [x] Service inquiry received

### 7.2 Notification Display
- **Current State**: None
- **Tasks**:
  - [x] Add notification bell icon in navigation
  - [x] Show unread count on bell (red badge)
  - [x] Dropdown menu showing recent notifications
  - [x] Toast notifications for real-time events
  - [x] Full notifications page with filters and sorting
  - [x] Mark all as read option

---

## 8. SEARCH & DISCOVERY (LOW-MEDIUM PRIORITY)

### 8.1 Advanced Search
- **Current State**: Basic search by service title
- **Tasks**:
  - [x] Improve search to include:
    - [x] Provider name search
    - [x] Service category/tags
    - [x] Location radius search
    - [x] Price range search
    - [x] Availability/response time
  - [x] Search autocomplete suggestions
  - [x] Search history (last 5 searches)
  - [x] Save search as custom filter

### 8.2 Recommendations
- **Current State**: No recommendations
- **Tasks**:
  - [x] Show "Recommended for you" services based on:
    - [x] Search history
    - [x] Recent views
    - [x] Similar to saved jobs
  - [x] Show "Popular this week" services
  - [x] Show "Recently joined providers"

---

## 9. DASHBOARD IMPROVEMENTS (MEDIUM PRIORITY)

### 9.1 Provider Dashboard
- **Current State**: Shows services list, basic stats
- **Tasks**:
  - [x] Add widgets:
    - [x] Recent inquiries/bids counter
    - [x] Pending jobs count
    - [x] Earnings/revenue summary
    - [x] Rating trend chart
    - [x] Response rate percentage
  - [x] Quick actions:
    - [x] Create new service (shortcut)
    - [x] View new bids
    - [x] View pending jobs
    - [x] View messages
  - [x] Activity feed:
    - [x] Recent bids received
    - [x] Job status updates
    - [x] New reviews posted
    - [x] Messages from clients

### 9.2 Client Dashboard
- **Current State**: Shows posted jobs, basic stats
- **Tasks**:
  - [x] Add widgets:
    - [x] Active jobs counter
    - [x] Bids received (total)
    - [x] Budget spent / remaining
    - [x] Average spend per project
    - [x] Satisfaction rating from providers
  - [x] Quick actions:
    - [x] Post new job (shortcut)
    - [x] View all bids
    - [x] View ongoing jobs
    - [x] View messages
  - [x] Activity feed:
    - [x] New bids on jobs
    - [x] Provider status updates
    - [x] Job completions
    - [x] Messages from providers

---

## 10. DATABASE & DATA INTEGRITY (LOW PRIORITY)

### 10.1 Data Validation
- **Current State**: Basic model validation
- **Tasks**:
  - [x] Ensure data constraints:
    - [x] Job budget > 0
    - [x] Bid amount > 0
    - [x] Service price > 0
    - [x] Rating 1-5 only
  - [x] Cascade deletes handled properly
  - [x] Prevent orphaned records

### 10.2 Database Backups
- **Current State**: No backup strategy
- **Tasks**:
  - [x] Implement automatic daily backups
  - [x] Test restore procedure
  - [x] Document backup location and process

---

## 11. SECURITY & PERFORMANCE (LOW-MEDIUM PRIORITY)

### 11.1 Security Fixes
- **Current State**: Basic auth in place
- **Tasks**:
  - [x] Ensure CSRF protection on all forms
  - [x] Validate all user inputs on backend
  - [x] Sanitize message content (prevent XSS)
  - [x] Rate limiting on API endpoints
  - [x] Prevent mass messaging/spam
  - [x] Secure password requirements
  - [x] Add two-factor authentication (optional)

### 11.2 Performance Optimization
- **Current State**: No optimization
- **Tasks**:
  - [x] Add database indexes on frequently queried fields:
    - [x] Message.recipient
    - [x] Message.sender
    - [x] Job.status
    - [x] Bid.job
  - [x] Implement pagination for lists:
    - [x] Messages (20 per page)
    - [x] Bids (10 per page)
    - [x] Jobs/Services (10-20 per page)
  - [x] Add API response caching where appropriate
  - [x] Lazy load images
  - [x] Minify CSS/JS for production

---

## 12. DEPLOYMENT & DEVOPS (LOW PRIORITY)

### 12.1 Production Readiness
- **Current State**: Development only
- **Tasks**:
  - [ ] Set up production server (DigitalOcean, Heroku, AWS, etc.)
  - [ ] Configure environment variables securely
  - [ ] Set up SSL/TLS certificates
  - [ ] Configure email backend for notifications
  - [ ] Set up static file serving
  - [ ] Configure database backups
  - [ ] Set up error logging/monitoring

### 12.2 CI/CD Pipeline
- **Current State**: Manual deployment
- **Tasks**:
  - [ ] Set up GitHub Actions for:
    - [ ] Running tests on push
    - [ ] Code quality checks
    - [ ] Automated deployment to staging
    - [ ] Automated deployment to production (with approval)

---

## PRIORITY ORDER FOR COMPLETION

### Phase Completion Tracker
- [x] Phase 1 ? Messaging, inbox, and job management now live with front-end UI and server-side validation.
- [x] Phase 2 ? Bidding, job detail, and profile experiences implemented end-to-end.
- [x] Phase 3 ? Reviews, notifications, dashboard widgets, and search/filter improvements are available.
- [ ] Phase 4 ? Deployment and hardening tasks remain outstanding.

### PHASE 1 (CRITICAL - Complete First):
1. Fix 403 errors on message posting
2. Complete message system (history, notifications)
3. Implement inbox with unread counter
4. Fix job status management

### PHASE 2 (HIGH - Core Features):
5. Implement bidding system (model, API, UI)
6. Complete job listing and filtering
7. Add job detail view
8. Implement user profile page

### PHASE 3 (MEDIUM - Polish):
9. Add reviews and ratings UI
10. Implement notifications system
11. Improve dashboard widgets
12. Add search enhancements

### PHASE 4 (LOW - Optional/Nice-to-have):
13. Add two-factor authentication
14. Performance optimization
15. Deployment setup
16. CI/CD pipeline

---

## TESTING CHECKLIST

Before considering features "done", test:
- [ ] User can send and receive messages
- [ ] Message history displays correctly
- [ ] Unread count updates in real-time
- [ ] Job status changes reflect immediately
- [ ] Bids can be placed and accepted
- [ ] Reviews can be posted and displayed
- [ ] All API endpoints return correct status codes
- [ ] Permission checks work (users can't edit others' data)
- [ ] Error messages are helpful and clear
- [ ] UI is responsive on mobile
- [ ] No console errors
- [ ] All forms validate input
- [ ] CSRF tokens work correctly

---

## ESTIMATED TIMELINE

- Phase 1: 2-3 days
- Phase 2: 3-4 days
- Phase 3: 2-3 days
- Phase 4: 2-3 days

**Total: 1-2 weeks to MVP with all core features working**

---

## NOTES

- Current database has sample data: 11 users, 8 services, 5 jobs
- GitHub repo: https://github.com/Blessing-Mbalaka/vashandi-workers-app
- All API endpoints use DRF with ViewSets
- Frontend is vanilla JavaScript (no framework)
- Dark theme UI implemented with CSS gradients
