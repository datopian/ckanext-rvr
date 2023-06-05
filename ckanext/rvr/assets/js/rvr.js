this.ckan.module('arrow-dropdown', function (jQuery, _) {
    return {
      options: {
        arrow: null
      },
      initialize: function () {
        this.el.select2({
          minimumResultsForSearch: Infinity
        });
      }
    };
  });
  