// SVG Map Search helpers
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

// Mandatory fields helpers
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

function checkTitle() {
  if (document.getElementById("field-title").value == "") {
      return false;
  }
}

function checkGroups() {
  if (document.getElementById("field-groups__1__id").value == "") {
    return false;
  }
}

function checkOrg() {
  if (document.getElementById("field-organizations").value == "") {
    return false;
  }
}

function checkNotes() {
  if (document.getElementById("field-notes").value == "") {
    return false;
  }
}

function checkAll() {
  if (checkTitle() == false || checkGroups() == false || checkOrg() == false || checkNotes() == false) {
    return false;
  } else {
    return true;
  }
}

function setButtonTooltip() {
  var error_title = "";
  var error_notes = "";
  var error_groups = "";
  var error_org = "";

  if (checkTitle() == false) {
    error_title =  "\tName: Fehlender Wert\n";
  }
  if (checkNotes() == false) {
    error_notes =  "\tBeschreibung: Fehlender Wert\n";
  }
  if (checkGroups() == false) {
    error_groups =  "\tGruppen: Fehlender Wert\n";
  }
  if (checkOrg() == false) {
    error_org =  "\tOrganisation: Fehlender Wert\n";
  }

  var error_message = "Das Formular enthält unzulässige Einträge:\n" + error_title + error_notes + error_org + error_groups;

  return error_message;
}

function groupChange() {
  if (checkAll() == false) {
    // Set the button class="btn btn-primary" in div class="form-actions" to disabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = true;
    // Set the tooltip of the button class="btn btn-primary" in div class="form-actions" to the error message
    document.getElementsByClassName("btn btn-primary")[0].title = setButtonTooltip();
  } else {
    // Set the button class="btn btn-primary" in div class="form-actions" to enabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = false;
    document.getElementsByClassName("btn btn-primary")[0].title = "";
  }
}

function orgChange() {
  if (checkAll() == false) {
    // Set the button class="btn btn-primary" in div class="form-actions" to disabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = true;
    // Set the tooltip of the button class="btn btn-primary" in div class="form-actions" to the error message
    document.getElementsByClassName("btn btn-primary")[0].title = setButtonTooltip();
  } else {
    // Set the button class="btn btn-primary" in div class="form-actions" to enabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = false;
    document.getElementsByClassName("btn btn-primary")[0].title = "";
  }
}

document.getElementById("field-notes").addEventListener("change", function(event) {
  if (checkAll() == false) {
    // Set the button class="btn btn-primary" in div class="form-actions" to disabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = true;
    // Set the tooltip of the button class="btn btn-primary" in div class="form-actions" to the error message
    document.getElementsByClassName("btn btn-primary")[0].title = setButtonTooltip();
  } else {
    // Set the button class="btn btn-primary" in div class="form-actions" to enabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = false;
    document.getElementsByClassName("btn btn-primary")[0].title = "";
  }
});

document.getElementById("field-title").addEventListener("change", function(event) {
  if (checkAll() == false) {
    // Set the button class="btn btn-primary" in div class="form-actions" to disabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = true;
    // Set the tooltip of the button class="btn btn-primary" in div class="form-actions" to the error message
    document.getElementsByClassName("btn btn-primary")[0].title = setButtonTooltip();
  } else {
    // Set the button class="btn btn-primary" in div class="form-actions" to enabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = false;
    document.getElementsByClassName("btn btn-primary")[0].title = "";
  }
});

// On submit form event listener
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

// On body change event listener
document.addEventListener("DOMContentLoaded", function(event) {
  if ( checkAll() == false) {
    // Set the button class="btn btn-primary" in div class="form-actions" to enabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = true;
    document.getElementsByClassName("btn btn-primary")[0].title = setButtonTooltip();
  } else {
    // Set the button class="btn btn-primary" in div class="form-actions" to enabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = false;
  }
});

