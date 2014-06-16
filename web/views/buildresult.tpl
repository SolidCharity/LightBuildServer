<html>
<head><title>Build Result for {{username}}/{{projectname}}/{{packagename}}/{{branchname}}</title>
<script type="text/JavaScript">
function timedRefresh(timeoutPeriod) {
        if (timeoutPeriod > 0) {
		setTimeout("location.reload(true);",timeoutPeriod);
	}
}
</script>
</head>
<body onload="JavaScript:timedRefresh({{timeoutInSeconds}}*1000);">
	<a name="top"><h2>Build Result for {{username}}/{{projectname}}/{{packagename}}/{{branchname}}</h2>
	<a href="/detail/{{username}}/{{projectname}}/{{packagename}}">back to package page</a>
	% if not timeoutInSeconds > 0:
		<br/><br/><a href="#bottom">go to bottom of this page</a>
	% end
	<pre style="white-space:pre-wrap;">
{{buildresult}}
	</pre>
        <a name="bottom">
	<a href="/detail/{{username}}/{{projectname}}/{{packagename}}">back to package page</a>
	% if not timeoutInSeconds > 0:
		<br/><br/><a href="#top">go to top of this page</a>
	% end
</body>
</html>
