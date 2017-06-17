require("bootstrap/dist/css/bootstrap.css");
require("bootstrap/dist/css/bootstrap-theme.css");
require('font-awesome/scss/font-awesome.scss');
require("wdf/wdf_view.css");
require("./style.scss");


var _ = require('lodash');
var u$ = require('wdf/utils');

var $ = window.jQuery = window.$ = require("jquery");
require("bootstrap/dist/js/bootstrap");

var path_template = _.template(require('raw!./templates/path.html'));

var WebFile = require('./WebFile');

var current_file;
window.onpopstate = function(event){
    navigate(event.state.path);
};

function navigate(path, stateAction, reload) {
    if (path.length > 0) {
        if( path[0] !== '/' ){
            path = current_file.path() + path ;
        }
        reload = _.isUndefined(reload) ? true : reload;
        current_file = new WebFile(path);
        var loading = current_file;
        if (history) {
            var method = 'replace' === stateAction ? 'replaceState' : 'pushState';
            window.history[method]({path: path}, current_file.name, current_file.path());
        }
        document.title = current_file.name;
        $('#header').html(path_template({
            file: current_file
        }));
        if (!reload) return;
        var url = '/.raw' + current_file.path();
        $('#main').html('');
        $.ajax({
            url: url,
            dataType: 'text',
            success: function (data, status, res) {
                if (loading == current_file) {
                    current_file.setContent(res, status, data);
                    var html = current_file.render();
                    if (!_.isNull(html)) {
                        $('#main').html(html);
                    }
                }
            }
        });
    }
}

function findAttribute(e,attr_name,depth){
    depth = depth || 3 ;
    var v ;
    for (var i = 0 ; i < depth ; i++){
        v = e.getAttribute(attr_name);
        if( ! u$.isNullish(v) ){
            return v;
        }
        e = e.parentElement;
    }
}

$(function(){
    $('#header').on('call_navigate',function(e){
        var d = e.originalEvent.detail;
        navigate(d.path, d.stateAction, d.reload );
    });
    $(document).on('click','[data-href]',function(e){
        navigate(findAttribute(e.target,'data-href'),true);
    });
    $(document).on('click','a.wdf_link',function(e){
        navigate(findAttribute(e.target,'href'),true);
        return false;
    });
    navigate(window.location.pathname);
});