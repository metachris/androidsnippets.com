/* Author: 

$(document).ready(function() {
});

*/

var is_editor = false;

function ui_to_editor() {
    $("#view_title").hide();
    $("#edit_title").show();
    //$("#view_description").hide();
    $("#view_description").hide();
    $("#edit_description").show();
    $("#code").hide();
    $("#edit_code").show();
    $("#editbox").show();
    $("#subtitle").hide();
    $("#comments").hide();
    
    $("#btn_edit .ui-button-text").html("Cancel");
}

function ui_to_viewmode() {
    $("#view_title").show();
    $("#edit_title").hide();
    $("#view_description").show();
    $("#edit_description").hide();
    $("#code").show();
    $("#editbox").hide();
    $("#edit_code").hide();
    $("#subtitle").show();
    $("#comments").show();
    
    $("#btn_edit .ui-button-text").html("Edit");
}

function _toggle_ui_to_editor() {
    if (is_editor)
        ui_to_viewmode();
    else
        ui_to_editor();
    is_editor = !is_editor;
}

var previewWindow;    
function preview() {
    var form = document.createElement("form");
    form.setAttribute("method", "post");
    form.setAttribute("action", "/preview");
    
    // setting form target to a window named 'formresult'
    form.setAttribute("target", "previewWindow");
    form.style.display = "none";
    
    var hiddenField = document.createElement("input");              
    hiddenField.setAttribute("name", "title");
    hiddenField.setAttribute("value", encodeURI($("#title").val()));
    form.appendChild(hiddenField);

    var hiddenField = document.createElement("input");              
    hiddenField.setAttribute("name", "desc");
    hiddenField.setAttribute("value", encodeURI($("#desc").val()));
    form.appendChild(hiddenField);

    var hiddenField = document.createElement("input");              
    hiddenField.setAttribute("name", "code");
    hiddenField.setAttribute("value", encodeURI($("#input_code").val()));
    form.appendChild(hiddenField);

    document.body.appendChild(form);
        
    if (!previewWindow || previewWindow.closed) {
        // opens a new window with the edit
        previewWindow = window.open("/preview", 'previewWindow',
        'left=20,top=20,width=600,height=500,toolbar=0,location=0,resizable=0,menubar=0,status=0');
    } else {
        previewWindow.focus();
    }

    form.submit();
}


function follow() {
    alert("follow");
}