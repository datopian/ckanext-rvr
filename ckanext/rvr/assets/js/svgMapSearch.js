function maximizeMap() {
    var mapMaximized = document.getElementById("maximized");
    var mapMinimized = document.getElementById("minimized");
    mapMaximized.style.display = "block";
    mapMinimized.style.display = "none";
}

function minimizeMap() {
    var mapMaximized = document.getElementById("maximized");
    var mapMinimized = document.getElementById("minimized");
    mapMaximized.style.display = "none";
    mapMinimized.style.display = "block";
}

function getSelectedOptions(sel) {
    var opts = [],
      opt;
    var len = sel.options.length;
    for (var i = 0; i < len; i++) {
      opt = sel.options[i];
  
      if (opt.selected) {
        opts.push(opt.value);
      }
    }
    opts = opts.filter(function(item, pos) {
        return opts.indexOf(item) == pos;
    });

    var group_string = document.getElementsByName("group_string")[0].value = opts.join("___");

    return group_string;
}

document.getElementById("dataset-edit").addEventListener("submit", function(event) {
    // Get selected options from the element with id="field-groups__0__id"
    var selectedOptions = getSelectedOptions(document.getElementById("field-groups__1__id"));
    var groups_dict = [];
    //  Frome selectedOptions string to array
    var selectedOptionsArray = selectedOptions.split("___");
    // Loop through the selectedOptionsArray and add the group object to the groups_dict
    for (var i = 0; i < selectedOptionsArray.length; i++) {
        groups_dict[i] = {"id":selectedOptionsArray[i]};
    }
    // Set the value of the field with name="group_string" to the selectedOptions array
    document.getElementsByName("group_string")[0].value = selectedOptions;
    
});