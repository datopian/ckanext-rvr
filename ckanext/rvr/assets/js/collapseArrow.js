this.ckan.module('collapse-arrow', function($, _) {
    return {
      initialize: function() {
        this.setupCollapseToggle();
      },
  
      setupCollapseToggle: function() {
        var toggleElements = this.el

        if (toggleElements.length === 0) {
          return;
        }
        toggleElements.on('click', function() {
          var spanElement = $(this).find('span');  
          spanElement.toggleClass('collapse-arrow collapsed-arrow');
        });
      }
    };
  });