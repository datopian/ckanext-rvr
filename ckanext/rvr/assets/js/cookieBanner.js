/* 
 * Self-hosted cookie consent banner
 * No external API dependencies - stores consent in localStorage
 */
ckan.module('cookie_banner', function (jQuery) {
    return {
        initialize: function () {
            var self = this;
            this.sandbox_ref = this.sandbox;
            this.el.removeClass('js-hide');
            this.consent = undefined;
            this.applyConsent();
            
            // Check if user has already made a consent choice
            if (!this.hasConsent()) {
                this.showBanner();
            } else {
                // Keep settings available after navigation or reload.
                this.minimizeBanner();
            }
            
            // Set up event handlers
            this.el.on('click', '.cookie-banner__accept-all', function(e) {
                e.preventDefault();
                self.acceptAll();
            });
            
            this.el.on('click', '.cookie-banner__reject', function(e) {
                e.preventDefault();
                self.rejectOptional();
            });
            
            this.el.on('click', '.cookie-banner__toggle-details', function(e) {
                e.preventDefault();
                self.toggleDetails();
            });
            
            this.el.on('change', '.cookie-banner__analytics-toggle', function(e) {
                self.saveCustomPreferences();
            });
            
            this.el.on('click', '.cookie-banner__close', function(e) {
                e.preventDefault();
                self.minimizeBanner();
            });
            
            this.el.on('click', '.cookie-banner__minimized-content', function(e) {
                e.preventDefault();
                self.showBanner();
            });
        },
        
        hasConsent: function() {
            return this.getConsent() !== null;
        },
        
        getConsent: function() {
            // Cache consent for this page, including when persistence is unavailable.
            if (this.consent !== undefined) {
                return this.consent;
            }
            this.consent = null;
            try {
                var stored = localStorage.getItem('cookie_consent');
                var consent = stored ? JSON.parse(stored) : null;
                if (consent && consent.necessary === true && typeof consent.analytics === 'boolean') {
                    this.consent = consent;
                }
            } catch (e) {
                // Blocked storage or invalid JSON means no saved consent.
            }
            return this.consent;
        },
        
        saveConsent: function(analytics) {
            var consent = {
                necessary: true,  // Always true
                analytics: analytics,
                timestamp: new Date().toISOString()
            };
            this.consent = consent;
            try {
                localStorage.setItem('cookie_consent', JSON.stringify(consent));
            } catch (e) {
                // Retain the choice in memory if storage is blocked or full.
            }
            this.applyConsent();
        },
        
        applyConsent: function() {
            var consent = this.getConsent();
            if (consent && consent.analytics) {
                // Enable analytics
                this.sandbox_ref.publish('analytics_enabled', true);
            } else {
                // Disable analytics
                this.sandbox_ref.publish('analytics_enabled', false);
            }
        },
        
        acceptAll: function() {
            this.saveConsent(true);
            this.hideBanner();
        },
        
        rejectOptional: function() {
            this.saveConsent(false);
            this.hideBanner();
        },
        
        saveCustomPreferences: function() {
            var analyticsEnabled = this.el.find('.cookie-banner__analytics-toggle').is(':checked');
            this.saveConsent(analyticsEnabled);
        },
        
        showBanner: function() {
            this.el.removeClass('js-hide cookie-banner--hidden cookie-banner--minimized');
            this.el.addClass('cookie-banner--visible');
            
            // Pre-populate checkbox if consent exists
            var consent = this.getConsent();
            this.el.find('.cookie-banner__analytics-toggle').prop('checked', !!(consent && consent.analytics));
        },
        
        hideBanner: function() {
            this.minimizeBanner();
        },
        
        minimizeBanner: function() {
            this.el.removeClass('cookie-banner--visible cookie-banner--hidden');
            this.el.addClass('cookie-banner--minimized');
        },
        
        toggleDetails: function() {
            var details = this.el.find('.cookie-banner__details');
            var toggleBtn = this.el.find('.cookie-banner__toggle-details');
            
            if (details.hasClass('cookie-banner__details--visible')) {
                details.removeClass('cookie-banner__details--visible');
                toggleBtn.text('Details anzeigen');
            } else {
                details.addClass('cookie-banner__details--visible');
                toggleBtn.text('Details ausblenden');
            }
        }
    };
});
