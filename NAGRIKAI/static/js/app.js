/**
 * NAGRIK AI - Delhi Civic Problem Dashboard Controller
 * Full integration: Category Filtering, Groq LLM Solutions, Upvoting/Downvoting,
 * Interactive Delhi Leaflet Map, Chart.js Trend Graphs, ML Moderation.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Global State
  const state = {
    currentCategory: "All",
    currentZone: "All",
    currentSearch: "",
    currentTab: "home",
    limit: 15,
    offset: 0,
    totalPosts: 0,
    posts: [],
    loading: false,
    mapInitialized: false,
    chartInitialized: false,
    leafletMap: null,
    trendChart: null,
    statsData: null,
    trendMetric: "all"
  };

  // DOM Elements
  const feedContainer = document.getElementById("feedContainer");
  const feedCountBadge = document.getElementById("feedCountBadge");
  const filterCurrentTag = document.getElementById("filterCurrentTag");
  const filterZoneTag = document.getElementById("filterZoneTag");
  const feedPaginationRow = document.getElementById("feedPaginationRow");
  const btnLoadMore = document.getElementById("btnLoadMore");
  const globalSearchInput = document.getElementById("globalSearchInput");
  const searchClearBtn = document.getElementById("searchClearBtn");
  const categoryWidgetList = document.getElementById("categoryWidgetList");
  const postModal = document.getElementById("postModal");
  const authModal = document.getElementById("authModal");
  const openPostBtn = document.getElementById("openPostBtn");
  const cancelPostBtn = document.getElementById("cancelPostBtn");
  const uploadPostBtn = document.getElementById("uploadPostBtn");
  const postTitle = document.getElementById("postTitle");
  const postLocation = document.getElementById("postLocation");
  const postCategory = document.getElementById("postCategory");
  const postDescription = document.getElementById("postDescription");
  const postImageInput = document.getElementById("postImageInput");
  const postImagePreview = document.getElementById("postImagePreview");
  const moderationAlert = document.getElementById("moderationAlert");
  const moderationAlertBody = document.getElementById("moderationAlertBody");
  const profileNavBtn = document.getElementById("profileNavBtn");
  const currentProfileName = document.getElementById("currentProfileName");
  const profileAvatarCircle = document.getElementById("profileAvatarCircle");
  const authForm = document.getElementById("authForm");

  let currentUploadedFile = null;

  // Initialize
  initApp();

  async function initApp() {
    await loadCurrentUser();
    await loadCategoryCounts();
    await fetchPosts(true);
    setupEventListeners();
  }

  function setupEventListeners() {
    // Search input with debounce
    let searchTimer = null;
    if (globalSearchInput) {
      globalSearchInput.addEventListener("input", (e) => {
        const val = e.target.value.trim();
        state.currentSearch = val;
        if (searchClearBtn) {
          searchClearBtn.style.display = val ? "block" : "none";
        }
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
          fetchPosts(true);
        }, 300);
      });
    }

    if (searchClearBtn) {
      searchClearBtn.addEventListener("click", () => {
        globalSearchInput.value = "";
        state.currentSearch = "";
        searchClearBtn.style.display = "none";
        fetchPosts(true);
      });
    }

    // Post modal open / close
    if (openPostBtn) openPostBtn.addEventListener("click", openCreatePostModal);
    if (cancelPostBtn) cancelPostBtn.addEventListener("click", closeCreatePostModal);
    if (profileNavBtn) profileNavBtn.addEventListener("click", () => authModal.classList.add("open"));

    // Modal background close
    [postModal, authModal].forEach(modal => {
      if (modal) {
        modal.addEventListener("click", (e) => {
          if (e.target === modal) modal.classList.remove("open");
        });
      }
    });

    // Post image preview
    if (postImageInput) {
      postImageInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (file) {
          currentUploadedFile = file;
          const reader = new FileReader();
          reader.onload = (event) => {
            postImagePreview.src = event.target.result;
          };
          reader.readAsDataURL(file);
        }
      });
    }

    // Submit post
    if (uploadPostBtn) uploadPostBtn.addEventListener("click", handleCreatePost);

    // Auth form submit
    if (authForm) {
      authForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = document.getElementById("authName").value;
        const username = document.getElementById("authUsername").value;
        const password = document.getElementById("authPassword").value;

        try {
          const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, username, password })
          });
          const data = await res.json();
          if (data.success) {
            authModal.classList.remove("open");
            showToast(`Signed in as ${data.user.name} (${data.user.username})`, "success");
            if (currentProfileName) currentProfileName.innerText = data.user.username;
            if (profileAvatarCircle) profileAvatarCircle.innerText = (data.user.name || "A")[0].toUpperCase();
            fetchPosts(true);
          } else {
            showToast(data.error || "Login failed.", "error");
          }
        } catch (err) {
          console.error("Login failed:", err);
        }
      });
    }
  }

  // Fetch Current User
  async function loadCurrentUser() {
    try {
      const res = await fetch("/api/session");
      const data = await res.json();
      if (data.authenticated && data.user) {
        if (currentProfileName) currentProfileName.innerText = data.user.username;
        if (profileAvatarCircle) profileAvatarCircle.innerText = (data.user.name || "A")[0].toUpperCase();
        const authName = document.getElementById("authName");
        const authUsername = document.getElementById("authUsername");
        if (authName) authName.value = data.user.name;
        if (authUsername) authUsername.value = data.user.username;
      }
    } catch (err) {
      console.error("Error loading user:", err);
    }
  }

  // Category Filtering - Flow requested by user
  window.filterByCategory = function(category) {
    state.currentCategory = category;
    state.offset = 0;

    // Update pill buttons active state
    document.querySelectorAll(".cat-pill").forEach(pill => {
      if (pill.getAttribute("data-category") === category) {
        pill.classList.add("active");
      } else {
        pill.classList.remove("active");
      }
    });

    if (filterCurrentTag) {
      filterCurrentTag.innerText = `Category: ${category}`;
    }

    // If on map or statistics tab, switch back to feed
    if (state.currentTab !== "home" && state.currentTab !== "problems") {
      window.switchTab("home");
    }

    fetchPosts(true);
  };

  // Zone Filtering
  window.filterByZone = function(zone) {
    state.currentZone = zone;
    state.offset = 0;

    if (filterZoneTag) {
      if (zone === "All") {
        filterZoneTag.style.display = "none";
      } else {
        filterZoneTag.style.display = "inline";
        filterZoneTag.innerText = `• Zone: ${zone.toUpperCase()}`;
      }
    }

    fetchPosts(true);
  };

  // Tab Switcher: Home, Problems, Map, Statistics
  window.switchTab = function(tabName) {
    state.currentTab = tabName;

    // Sidebar active item
    document.querySelectorAll(".sidebar-nav-item").forEach(item => {
      if (item.getAttribute("data-tab") === tabName) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    // Tab pane display
    const paneFeed = document.getElementById("paneFeed");
    const paneMap = document.getElementById("paneMap");
    const paneStatistics = document.getElementById("paneStatistics");
    const heroBanner = document.getElementById("heroBanner");

    if (paneFeed) paneFeed.classList.remove("active");
    if (paneMap) paneMap.classList.remove("active");
    if (paneStatistics) paneStatistics.classList.remove("active");

    if (tabName === "home" || tabName === "problems") {
      if (paneFeed) paneFeed.classList.add("active");
      if (heroBanner) heroBanner.style.display = "flex";
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else if (tabName === "map") {
      if (paneMap) paneMap.classList.add("active");
      if (heroBanner) heroBanner.style.display = "none";
      initDelhiMap();
    } else if (tabName === "statistics") {
      if (paneStatistics) paneStatistics.classList.add("active");
      if (heroBanner) heroBanner.style.display = "none";
      initStatisticsView();
    }
  };

  // Fetch Posts from API
  async function fetchPosts(reset = false) {
    if (state.loading) return;
    state.loading = true;

    if (reset) {
      state.offset = 0;
      state.posts = [];
      if (feedContainer) {
        feedContainer.innerHTML = `
          <div class="feed-loading-state">
            <div class="loading-spinner"></div>
            <div>Loading verified Delhi civic issues...</div>
          </div>
        `;
      }
    }

    try {
      const url = new URL("/api/posts", window.location.origin);
      url.searchParams.set("category", state.currentCategory);
      url.searchParams.set("zone", state.currentZone);
      if (state.currentSearch) url.searchParams.set("search", state.currentSearch);
      url.searchParams.set("limit", state.limit);
      url.searchParams.set("offset", state.offset);

      const res = await fetch(url);
      const data = await res.json();

      state.totalPosts = data.total;
      if (reset) {
        state.posts = data.posts || [];
      } else {
        state.posts = state.posts.concat(data.posts || []);
      }

      state.offset += (data.posts || []).length;

      // Update count badge
      if (feedCountBadge) {
        feedCountBadge.innerText = `${data.total.toLocaleString()} Complaints`;
      }

      renderFeedCards();

      // Show or hide load more
      if (feedPaginationRow && btnLoadMore) {
        if (state.offset < state.totalPosts) {
          feedPaginationRow.style.display = "block";
          btnLoadMore.innerText = `Load More Complaints (${state.offset} of ${state.totalPosts})`;
        } else {
          feedPaginationRow.style.display = "none";
        }
      }
    } catch (err) {
      console.error("Error fetching posts:", err);
      if (feedContainer) {
        feedContainer.innerHTML = `<div style="text-align:center; padding: 40px; color: #ef4444; background: white; border-radius: 16px;">Failed to load complaints. Please check your network.</div>`;
      }
    } finally {
      state.loading = false;
    }
  }

  window.loadMorePosts = function() {
    fetchPosts(false);
  };

  // Render Feed Cards matching uploaded image layout exactly
  function renderFeedCards() {
    if (!feedContainer) return;

    if (state.posts.length === 0) {
      feedContainer.innerHTML = `
        <div style="text-align: center; padding: 60px 20px; background: white; border-radius: 16px; color: #64748b; border: 1px solid var(--border-light);">
          <div style="font-size: 32px; margin-bottom: 8px;">🔍</div>
          <div style="font-size: 16px; font-weight: 700; color: #1e293b;">No complaints found</div>
          <div style="font-size: 13.5px; margin-top: 4px;">No issues match your current filters. Try selecting "All" categories or reset search.</div>
        </div>
      `;
      return;
    }

    const colorClasses = ["c-blue", "c-green", "c-purple", "c-orange", "c-amber"];

    feedContainer.innerHTML = state.posts.map((post, idx) => {
      const authorInitial = (post.author_name || post.author_username || "A")[0].toUpperCase();
      const colorClass = colorClasses[Math.abs(hashCode(post.author_username)) % colorClasses.length];
      const isLiked = Boolean(post.user_liked);
      const userVote = post.user_solution_vote; // 'up', 'down', or null
      const zoneClass = (post.zone || "yellow").toLowerCase();
      const timeAgo = formatTimeAgo(post.created_at);

      // Delhi AI Solution
      const aiSolution = post.ai_solution || "Report directly via MCD 311 App. Zonal sanitary inspector or road maintenance division will inspect within 48 hours under Delhi Right to Service Act 2011.";
      const aiAuthority = post.ai_authority || "Municipal Corporation of Delhi (MCD) / PWD Delhi";
      const aiRules = post.ai_delhi_rules || "Delhi Right to Service (e-SLA) Act 2011 & DMC Act 1957";

      const commentsCount = (post.comments || []).length;
      const commentsHtml = (post.comments || []).map(c => `
        <div class="comment-item">
          <span class="comment-author">${escapeHtml(c.author_username)}:</span>
          <span>${escapeHtml(c.comment_text)}</span>
        </div>
      `).join("");

      return `
        <article class="post-card" id="post-card-${post.id}">
          <!-- Top Row: Avatar, Name, Location Pin, Menu -->
          <div class="post-header-row">
            <div class="post-author-group">
              <div class="post-avatar-circle ${colorClass}">${authorInitial}</div>
              <div class="post-meta-text">
                <span class="post-author-name">${escapeHtml(post.author_username)}</span>
                <span class="post-location-time">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                    <circle cx="12" cy="10" r="3"></circle>
                  </svg>
                  ${escapeHtml(post.location || "Delhi")} • ${timeAgo}
                  <span class="zone-chip-badge ${zoneClass}">${zoneClass} Zone</span>
                </span>
              </div>
            </div>

            <button class="post-menu-btn" title="More options" onclick="window.showToast('Grievance ID: DEL-${post.id} (Registered on GNCTD Portal)', 'info')">•••</button>
          </div>

          <!-- Middle Row: Issue Title & Description on Left, Photo on Right -->
          <div class="post-body-layout">
            <div class="post-text-side">
              <h3 class="post-issue-title">${escapeHtml(post.title || post.category + " Issue")}</h3>
              <p class="post-issue-desc">${escapeHtml(post.description)}</p>
            </div>

            ${post.image_url ? `
              <div class="post-image-side">
                <img src="${post.image_url}" alt="Problem photo" class="post-evidence-img" onerror="this.src='/static/assets/post_pothole.png'" />
              </div>
            ` : ""}
          </div>

          <!-- AI Proposed Solution under Delhi Municipal / GNCTD Rules -->
          <div class="post-ai-solution-box" id="ai-box-${post.id}">
            <div class="ai-solution-header">
              <span class="ai-solution-title">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="11" width="18" height="10" rx="2"></rect>
                  <circle cx="12" cy="5" r="2"></circle>
                  <path d="M12 7v4"></path>
                  <line x1="8" y1="16" x2="8" y2="16"></line>
                  <line x1="16" y1="16" x2="16" y2="16"></line>
                </svg>
                AI Solution (Delhi Municipal Framework)
              </span>
              <span class="ai-sla-tag">SLA: 24-72 hrs</span>
            </div>

            <div class="ai-solution-body" id="ai-solution-text-${post.id}">
              ${escapeHtml(aiSolution)}
            </div>

            <div class="ai-authority-line" id="ai-authority-line-${post.id}">
              <b>Designated Authority:</b> ${escapeHtml(aiAuthority)} | <b>Delhi Law:</b> ${escapeHtml(aiRules)}
            </div>

            <!-- Upvote / Downvote AI Solution -->
            <div class="ai-vote-row">
              <span class="ai-vote-prompt">Was this Delhi AI solution accurate?</span>
              <div class="ai-vote-buttons">
                <button class="btn-vote-ai ${userVote === 'up' ? 'voted-up' : ''}" id="btn-vote-up-${post.id}" onclick="window.voteSolution(${post.id}, 'up')" title="Upvote this solution">
                  <span>👍 Good</span>
                  <span id="vote-up-count-${post.id}">${post.solution_upvotes || 0}</span>
                </button>
                <button class="btn-vote-ai ${userVote === 'down' ? 'voted-down' : ''}" id="btn-vote-down-${post.id}" onclick="window.voteSolution(${post.id}, 'down')" title="Downvote this solution">
                  <span>👎 Bad</span>
                  <span id="vote-down-count-${post.id}">${post.solution_downvotes || 0}</span>
                </button>
                <button class="btn-ask-groq" id="btn-groq-${post.id}" onclick="window.askGroqLive(${post.id})" title="Ask Groq LLM to re-evaluate under latest Delhi rules">
                  <span>⚡ Ask Groq AI</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Post Engagement Footer: Heart Likes, Comments, Share -->
          <div class="post-actions-footer">
            <button class="action-btn ${isLiked ? 'liked' : ''}" id="btn-like-${post.id}" onclick="window.togglePostLike(${post.id})">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
              </svg>
              <span id="like-count-${post.id}">${post.likes_count || 0}</span>
            </button>

            <button class="action-btn" onclick="window.togglePostComments(${post.id})">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
              </svg>
              <span id="comment-count-${post.id}">${commentsCount}</span>
            </button>

            <button class="action-btn" onclick="window.sharePost(${post.id})">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
                <polyline points="16 6 12 2 8 6"></polyline>
                <line x1="12" y1="2" x2="12" y2="15"></line>
              </svg>
              <span>Share</span>
            </button>
          </div>

          <!-- Expandable Comments Drawer -->
          <div class="post-comments-panel" id="comments-panel-${post.id}">
            <div class="comment-list" id="comments-list-${post.id}">
              ${commentsHtml || '<div style="font-size: 12px; color: #94a3b8;">No comments yet. Share your community feedback!</div>'}
            </div>
            <div class="comment-input-row">
              <input type="text" class="comment-input" id="comment-input-${post.id}" placeholder="Write a civic comment..." onkeydown="if(event.key==='Enter') window.submitComment(${post.id})" />
              <button class="btn-comment-send" onclick="window.submitComment(${post.id})">Post</button>
            </div>
          </div>
        </article>
      `;
    }).join("");
  }

  // Vote on AI Solution (Upvote / Downvote)
  window.voteSolution = async function(postId, voteType) {
    try {
      const res = await fetch(`/api/posts/${postId}/vote-solution`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ vote_type: voteType })
      });
      const data = await res.json();
      if (data.success) {
        const upCountSpan = document.getElementById(`vote-up-count-${postId}`);
        const downCountSpan = document.getElementById(`vote-down-count-${postId}`);
        const btnUp = document.getElementById(`btn-vote-up-${postId}`);
        const btnDown = document.getElementById(`btn-vote-down-${postId}`);

        if (upCountSpan) upCountSpan.innerText = data.solution_upvotes;
        if (downCountSpan) downCountSpan.innerText = data.solution_downvotes;

        if (btnUp && btnDown) {
          btnUp.classList.remove("voted-up");
          btnDown.classList.remove("voted-down");
          if (data.user_vote === "up") btnUp.classList.add("voted-up");
          if (data.user_vote === "down") btnDown.classList.add("voted-down");
        }

        showToast(data.user_vote ? `Vote recorded for Delhi AI solution!` : `Vote removed`, "info");
      }
    } catch (err) {
      console.error("Error voting on solution:", err);
    }
  };

  // Live Groq LLM Solver for specific complaint
  window.askGroqLive = async function(postId) {
    const btn = document.getElementById(`btn-groq-${postId}`);
    const solutionText = document.getElementById(`ai-solution-text-${postId}`);
    const authorityLine = document.getElementById(`ai-authority-line-${postId}`);

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span>⚡ Groq Analyzing...</span>`;
    }

    try {
      const res = await fetch(`/api/posts/${postId}/ai-solve`, { method: "POST" });
      const data = await res.json();

      if (data.success) {
        if (solutionText) solutionText.innerText = data.ai_solution;
        if (authorityLine) {
          authorityLine.innerHTML = `<b>Designated Authority:</b> ${escapeHtml(data.ai_authority)} | <b>Delhi Law:</b> ${escapeHtml(data.ai_delhi_rules)}`;
        }
        showToast("Fresh AI resolution generated by Groq LLM under Delhi rules!", "success");
      } else {
        showToast("Groq LLM was unable to refresh solution.", "error");
      }
    } catch (err) {
      console.error("Groq AI solver error:", err);
      showToast("Error connecting to Groq API.", "error");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span>⚡ Ask Groq AI</span>`;
      }
    }
  };

  // Toggle Post Like
  window.togglePostLike = async function(postId) {
    try {
      const res = await fetch(`/api/posts/${postId}/like`, { method: "POST" });
      const data = await res.json();
      if (data.success) {
        const btn = document.getElementById(`btn-like-${postId}`);
        const countSpan = document.getElementById(`like-count-${postId}`);
        if (countSpan) countSpan.innerText = data.likes_count;
        if (btn) {
          if (data.liked) btn.classList.add("liked");
          else btn.classList.remove("liked");
        }
      }
    } catch (err) {
      console.error("Error toggling like:", err);
    }
  };

  // Toggle Comments Panel
  window.togglePostComments = function(postId) {
    const panel = document.getElementById(`comments-panel-${postId}`);
    if (panel) panel.classList.toggle("open");
  };

  // Submit Comment
  window.submitComment = async function(postId) {
    const input = document.getElementById(`comment-input-${postId}`);
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    try {
      const res = await fetch(`/api/posts/${postId}/comment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment: text })
      });
      const data = await res.json();
      if (!res.ok || data.flagged) {
        showToast(data.message || "Comment flagged for disrespectful language.", "error");
        return;
      }

      input.value = "";
      const list = document.getElementById(`comments-list-${postId}`);
      const countSpan = document.getElementById(`comment-count-${postId}`);
      if (countSpan) countSpan.innerText = data.comments_count;
      if (list) {
        list.innerHTML = data.comments.map(c => `
          <div class="comment-item">
            <span class="comment-author">${escapeHtml(c.author_username)}:</span>
            <span>${escapeHtml(c.comment_text)}</span>
          </div>
        `).join("");
      }
      showToast("Comment added!", "success");
    } catch (err) {
      console.error("Error submitting comment:", err);
    }
  };

  // Share Post
  window.sharePost = function(postId) {
    const shareUrl = `${window.location.origin}/#post-card-${postId}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      showToast(`Grievance link copied to clipboard! (ID: DEL-${postId})`, "success");
    }).catch(() => {
      showToast(`Grievance ID: DEL-${postId}`, "info");
    });
  };

  // Create Post Modal Handlers
  function openCreatePostModal() {
    hideModerationAlert();
    postModal.classList.add("open");
  }

  function closeCreatePostModal() {
    postModal.classList.remove("open");
    if (postTitle) postTitle.value = "";
    if (postDescription) postDescription.value = "";
    currentUploadedFile = null;
    hideModerationAlert();
  }

  async function handleCreatePost() {
    const title = postTitle.value.trim();
    const location = postLocation.value.trim() || "New Delhi";
    const category = postCategory.value;
    const description = postDescription.value.trim();

    if (!description) {
      showModerationAlert("Please enter a detailed description of the civic issue.");
      postDescription.focus();
      return;
    }

    uploadPostBtn.disabled = true;
    uploadPostBtn.innerText = "Validating with UPKAR-ML & Groq...";

    try {
      const formData = new FormData();
      formData.append("title", title || description.slice(0, 50));
      formData.append("location", location);
      formData.append("category", category);
      formData.append("description", description);
      if (currentUploadedFile) {
        formData.append("image_file", currentUploadedFile);
      } else {
        formData.append("image_url", postImagePreview.getAttribute("src"));
      }

      const res = await fetch("/api/posts", {
        method: "POST",
        body: formData
      });
      const data = await res.json();

      if (!res.ok || data.flagged) {
        showModerationAlert(data.message || "Your post was flagged by civic moderation.");
        uploadPostBtn.disabled = false;
        uploadPostBtn.innerText = "Submit & Generate AI Solution";
        return;
      }

      showToast("Civic problem published & AI resolution generated!", "success");
      closeCreatePostModal();
      loadCategoryCounts();
      fetchPosts(true);
    } catch (err) {
      console.error("Error creating post:", err);
      showModerationAlert("Failed to publish post. Please check connection.");
    } finally {
      uploadPostBtn.disabled = false;
      uploadPostBtn.innerText = "Submit & Generate AI Solution";
    }
  }

  function showModerationAlert(msg) {
    if (moderationAlert && moderationAlertBody) {
      moderationAlertBody.innerText = msg;
      moderationAlert.classList.add("visible");
    }
  }

  function hideModerationAlert() {
    if (moderationAlert) moderationAlert.classList.remove("visible");
  }

  // Load and Render Category Counts in Right Sidebar matching reference image
  async function loadCategoryCounts() {
    try {
      const res = await fetch("/api/categories");
      const counts = await res.json();
      renderCategoryWidget(counts);
    } catch (err) {
      console.error("Error loading categories:", err);
    }
  }

  function renderCategoryWidget(counts) {
    if (!categoryWidgetList) return;

    // Ordered matching Image:
    // Climate Issue, Healthcare, Education, Sanitation, Infrastructure
    const items = [
      { key: "Climate Issue", label: "Climate Issue", icon: "🍃", cssClass: "climate", count: counts["Climate Issue"] || 0 },
      { key: "Healthcare", label: "Healthcare", icon: "🩺", cssClass: "healthcare", count: counts["Healthcare"] || 0 },
      { key: "Education", label: "Education", icon: "📖", cssClass: "education", count: counts["Education"] || 0 },
      { key: "Sanitation", label: "Sanitation", icon: "🗑️", cssClass: "sanitation", count: counts["Sanitation"] || 0 },
      { key: "Infrastructure", label: "Infrastructure", icon: "🏗️", cssClass: "infrastructure", count: counts["Infrastructure"] || 0 }
    ];

    const maxCount = Math.max(...items.map(i => i.count), 200);

    categoryWidgetList.innerHTML = items.map(item => {
      const widthPct = item.count === 0 ? 2 : Math.min(100, Math.round((item.count / maxCount) * 98) + 2);
      return `
        <div class="category-row" onclick="window.filterByCategory('${item.key === 'Climate Issue' ? 'Climate' : item.key}')" title="Filter by ${item.label}">
          <div class="category-row-top">
            <div class="category-row-left">
              <div class="cat-circle-icon ${item.cssClass}">${item.icon}</div>
              <span class="cat-name-label">${item.label}</span>
            </div>
            <span class="cat-count-badge">${item.count}</span>
          </div>
          <div class="category-progress-track">
            <div class="category-progress-fill ${item.cssClass}" style="width: ${widthPct}%;"></div>
          </div>
        </div>
      `;
    }).join("");
  }

  // =========================================================================
  // INTERACTIVE DELHI MAP (Leaflet.js)
  // Shows Red, Yellow, Green Zones across Delhi
  // =========================================================================
  async function initDelhiMap() {
    if (state.mapInitialized) {
      setTimeout(() => {
        if (state.leafletMap) state.leafletMap.invalidateSize();
      }, 200);
      return;
    }

    const mapElement = document.getElementById("delhiLeafletMap");
    if (!mapElement) return;

    // Centered on NCT of Delhi
    const delhiCenter = [28.6139, 77.2090];
    const map = L.map("delhiLeafletMap", {
      zoomControl: true,
      scrollWheelZoom: true
    }).setView(delhiCenter, 11);

    // Clean OpenStreetMap tiles
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | NAGRIK AI Delhi GIS',
      maxZoom: 18
    }).addTo(map);

    state.leafletMap = map;
    state.mapInitialized = true;

    try {
      const res = await fetch("/api/map-locations");
      const data = await res.json();
      const locations = data.locations || [];

      locations.forEach(loc => {
        const color = loc.zone === "red" ? "#ef4444" : (loc.zone === "yellow" ? "#f59e0b" : "#10b981");
        const fillColor = loc.zone === "red" ? "#fee2e2" : (loc.zone === "yellow" ? "#fef3c7" : "#d1fae5");
        const radius = Math.min(26, Math.max(12, Math.round(loc.count * 0.4) + 8));

        // Pulsing Circle Marker
        const marker = L.circleMarker([loc.lat, loc.lng], {
          radius: radius,
          fillColor: color,
          color: "#ffffff",
          weight: 2.5,
          opacity: 1,
          fillOpacity: 0.82
        }).addTo(map);

        // Rich Popup
        const popupContent = `
          <div style="font-family: sans-serif; min-width: 200px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
              <strong style="font-size: 14px; color: #1e3a8a;">${escapeHtml(loc.location)}</strong>
              <span style="font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 9999px; background: ${fillColor}; color: ${color}; text-transform: uppercase;">
                ${loc.zone} zone
              </span>
            </div>
            <div style="font-size: 12.5px; margin-bottom: 8px; color: #475569;">
              Total Complaints: <b>${loc.count}</b>
            </div>
            <div style="font-size: 11.5px; color: #64748b; line-height: 1.4; margin-bottom: 8px;">
              • Infrastructure: ${loc.infra_count || 0}<br>
              • Sanitation: ${loc.sanit_count || 0}<br>
              • Education: ${loc.edu_count || 0}<br>
              • Healthcare: ${loc.health_count || 0}<br>
              • Climate: ${loc.climate_count || 0}
            </div>
            <button onclick="window.filterByMapLocation('${escapeHtml(loc.location)}')" 
                    style="width: 100%; padding: 6px 10px; background: #2563eb; color: white; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;">
              View Complaints (${loc.count})
            </button>
          </div>
        `;
        marker.bindPopup(popupContent);
      });
    } catch (err) {
      console.error("Error loading map points:", err);
    }
  }

  window.filterByMapLocation = function(locName) {
    state.currentSearch = locName;
    if (globalSearchInput) globalSearchInput.value = locName;
    window.switchTab("home");
    fetchPosts(true);
  };

  // =========================================================================
  // STATISTICAL OVERVIEW & CHARTS (Chart.js)
  // Most Common Complaints, Location Ranking, and Trend Graph (Increase/Decrease)
  // =========================================================================
  async function initStatisticsView() {
    try {
      const res = await fetch("/api/statistics");
      const data = await res.json();
      state.statsData = data;

      // Update KPI counters
      document.getElementById("statTotalComplaints").innerText = data.total_complaints.toLocaleString();
      document.getElementById("statRedCount").innerText = `${data.zone_counts.red} Hotspots`;
      document.getElementById("statYellowCount").innerText = `${data.zone_counts.yellow} Areas`;
      document.getElementById("statGreenCount").innerText = `${data.zone_counts.green} Sectors`;

      // Render Problem Clusters
      renderProblemClusters(data.problem_clusters || []);

      // Render Location Ranking Table
      renderLocationRanking(data.location_ranking || []);

      // Render Trend Chart
      renderTrendChart(data.trend_data || []);
    } catch (err) {
      console.error("Error loading statistics:", err);
    }
  }

  function renderProblemClusters(clusters) {
    const container = document.getElementById("problemClustersList");
    if (!container) return;

    const maxCount = Math.max(...clusters.map(c => c.count), 1);

    container.innerHTML = clusters.map(c => {
      const pct = Math.round((c.count / maxCount) * 100);
      return `
        <div class="cluster-item">
          <div class="cluster-header">
            <span>${escapeHtml(c.issue)}</span>
            <span style="color: #2563eb;">${c.count} cases</span>
          </div>
          <div class="cluster-bar-track">
            <div class="cluster-bar-fill" style="width: ${pct}%;"></div>
          </div>
        </div>
      `;
    }).join("");
  }

  function renderLocationRanking(locations) {
    const tbody = document.getElementById("locationRankingBody");
    if (!tbody) return;

    tbody.innerHTML = locations.slice(0, 10).map((loc, i) => {
      const zoneBadge = loc.zone === "red" 
        ? `<span class="zone-chip-badge red">Red</span>` 
        : (loc.zone === "yellow" ? `<span class="zone-chip-badge yellow">Yellow</span>` : `<span class="zone-chip-badge green">Green</span>`);

      return `
        <tr>
          <td><b>#${i + 1}</b> ${escapeHtml(loc.location)}</td>
          <td>${zoneBadge}</td>
          <td><b>${loc.count}</b></td>
          <td>
            <button onclick="window.filterByMapLocation('${escapeHtml(loc.location)}')" 
                    style="padding: 4px 8px; font-size: 11.5px; font-weight: 600; background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; cursor: pointer;">
              View Feed
            </button>
          </td>
        </tr>
      `;
    }).join("");
  }

  // Chart.js Trend Graph showing increase/decrease over months
  function renderTrendChart(trendData) {
    const canvas = document.getElementById("trendChartCanvas");
    if (!canvas) return;

    if (state.trendChart) {
      state.trendChart.destroy();
    }

    const labels = trendData.map(d => {
      const parts = d.month.split("-");
      const date = new Date(parts[0], parseInt(parts[1]) - 1, 1);
      return date.toLocaleString('default', { month: 'short', year: 'numeric' });
    });

    let datasets = [];

    if (state.trendMetric === "all") {
      datasets = [
        {
          label: "Reported Civic Issues",
          data: trendData.map(d => d.total),
          borderColor: "#2563eb",
          backgroundColor: "rgba(37, 99, 235, 0.12)",
          fill: true,
          tension: 0.35,
          borderWidth: 3,
          pointRadius: 4
        },
        {
          label: "Resolved / Action Taken",
          data: trendData.map(d => d.resolved),
          borderColor: "#10b981",
          backgroundColor: "transparent",
          borderDash: [5, 5],
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 3
        }
      ];
    } else if (state.trendMetric === "categories") {
      datasets = [
        {
          label: "Infrastructure",
          data: trendData.map(d => d.infrastructure),
          borderColor: "#f97316",
          backgroundColor: "transparent",
          tension: 0.35,
          borderWidth: 2
        },
        {
          label: "Sanitation",
          data: trendData.map(d => d.sanitation),
          borderColor: "#10b981",
          backgroundColor: "transparent",
          tension: 0.35,
          borderWidth: 2
        },
        {
          label: "Climate (Air/Dust)",
          data: trendData.map(d => d.climate),
          borderColor: "#22c55e",
          backgroundColor: "transparent",
          tension: 0.35,
          borderWidth: 2
        },
        {
          label: "Healthcare",
          data: trendData.map(d => d.healthcare),
          borderColor: "#ef4444",
          backgroundColor: "transparent",
          tension: 0.35,
          borderWidth: 2
        },
        {
          label: "Education",
          data: trendData.map(d => d.education),
          borderColor: "#8b5cf6",
          backgroundColor: "transparent",
          tension: 0.35,
          borderWidth: 2
        }
      ];
    } else {
      datasets = [
        {
          label: "Open / In Progress",
          data: trendData.map(d => d.total - d.resolved),
          borderColor: "#ef4444",
          backgroundColor: "rgba(239, 68, 68, 0.1)",
          fill: true,
          tension: 0.35,
          borderWidth: 2.5
        },
        {
          label: "Resolved Under SLA",
          data: trendData.map(d => d.resolved),
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          fill: true,
          tension: 0.35,
          borderWidth: 2.5
        }
      ];
    }

    state.trendChart = new Chart(canvas, {
      type: "line",
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
            labels: {
              boxWidth: 12,
              font: { family: "sans-serif", size: 12, weight: 600 }
            }
          },
          tooltip: {
            mode: "index",
            intersect: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: "#f1f5f9" }
          },
          x: {
            grid: { display: false }
          }
        }
      }
    });
  }

  window.updateTrendMetric = function(metric) {
    state.trendMetric = metric;
    document.querySelectorAll(".chart-toggle-btn").forEach(btn => {
      btn.classList.remove("active");
    });
    event.target.classList.add("active");
    if (state.statsData) {
      renderTrendChart(state.statsData.trend_data || []);
    }
  };

  // Helper Utilities
  function formatTimeAgo(dateString) {
    if (!dateString) return "recently";
    const date = new Date(dateString.replace(" ", "T"));
    const now = new Date();
    const diffSec = Math.max(0, Math.floor((now - date) / 1000));

    if (diffSec < 60) return "just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin} min ago`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour} hours ago`;
    const diffDay = Math.floor(diffHour / 24);
    if (diffDay < 30) return `${diffDay} days ago`;
    const diffMonth = Math.floor(diffDay / 30);
    return `${diffMonth} months ago`;
  }

  function hashCode(str) {
    let hash = 0;
    if (!str) return hash;
    for (let i = 0; i < str.length; i++) {
      hash = (hash << 5) - hash + str.charCodeAt(i);
      hash |= 0;
    }
    return hash;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function showToast(message, type = "info") {
    let container = document.querySelector(".toast-container");
    if (!container) {
      container = document.createElement("div");
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 4000);
  }

  window.showToast = showToast;
});
