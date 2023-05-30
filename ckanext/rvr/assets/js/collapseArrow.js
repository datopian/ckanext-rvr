this.ckan.module('collapse-arrow', function($, _) {
    return {
      initialize: function() {
        this.setupCollapseToggle();
      },
  
      setupCollapseToggle: function() {
        var toggleElements = this.el

        toggleElements.on('click', function(event) {
          if(toggleElements.attr('aria-controls') === 'collapse-dataset-map'){
            
            if ($('body').hasClass('dataset-map-expanded')) {
              $('body').removeClass('dataset-map-expanded');
            }
            // Prevents the collapse 
            toggleElements.removeAttr('data-toggle');
            if (event.target.className === 'action') {
              // allow clear link to click through
              return;
            }
            toggleElements.attr('data-toggle', 'collapse');
          }
          var spanElement = $(this).find('span');  
          spanElement.toggleClass('collapse-arrow collapsed-arrow');
        });
      }
    };
  });