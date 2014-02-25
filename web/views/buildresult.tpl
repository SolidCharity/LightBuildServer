<html>
<head><title>Build Result</title>
<script type="text/JavaScript">
function timedRefresh(timeoutPeriod) {
	setTimeout("location.reload(true);",timeoutPeriod);
}
</script>
</head>
<!-- refresh every 2 seconds -->
<body onload="JavaScript:timedRefresh(2000);">
	<h2>Build Result</h2>
	<pre>
{{buildresult}}
	</pre>
	<a href="/">back to main page</a>	
</body>
</html>
