# -*- coding: utf-8 -*-
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<%inherit file="/diracPage.mako" />

<%def name="head_tags()">
${ h.javascript_link( "/javascripts/lovCombo.js" ) }
${ h.javascript_link( "/javascripts/dencodelight.js" ) }
${ h.javascript_link( "/javascripts/FileUploadField.js" ) }
${ h.javascript_link( "/javascripts/jobs/Lib.js" ) }
${ h.javascript_link( "/javascripts/jobs/Plot.js" ) }
${ h.javascript_link( "/javascripts/jobs/Launchpad.js" ) }
${ h.javascript_link( "/javascripts/jobs/JobMonitor.js" ) }
${ h.stylesheet_link( "/stylesheets/lovCombo.css" ) }
${ h.stylesheet_link( "/stylesheets/fileupload.css" ) }

</%def>

<%def name="body()">
<script type="text/javascript">
  initLoop(${c.select});
</script>
</%def>
