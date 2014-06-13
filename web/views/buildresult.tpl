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
	<h2>Build Result for {{username}}/{{projectname}}/{{packagename}}/{{branchname}}</h2>
	<pre style="white-space:pre-wrap;">
{{buildresult}}
	</pre>
	<a href="/detail/{{username}}/{{projectname}}/{{packagename}}">back to package page</a>
</body>
</html>
