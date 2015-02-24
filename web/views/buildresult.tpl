% include('header.tpl', title="Build Result for "+username+"/"+projectname+"/"+packagename+"/"+branchname, page='package', branchname=branchname, buildtarget=buildtarget)
<script type="text/JavaScript">
function timedRefresh(timeoutPeriod) {
        if (timeoutPeriod > 0) {
		setTimeout("location.reload(true);",timeoutPeriod);
	}
}
timedRefresh({{timeoutInSeconds}}*1000);
</script>
    <div class="container">
      <div class="row">
        <h2>Build Result for {{username}}/{{projectname}}/{{packagename}}/{{branchname}}</h2>
	% if not timeoutInSeconds > 0:
		<a href="#bottom">go to bottom of this page</a>
	% end
	<pre style="white-space:pre-wrap;">
{{buildresult}}
	</pre>
        <a name="bottom"></a>
	% if not timeoutInSeconds > 0:
		<a href="#top">go to top of this page</a>
	% end
      </div>
    </div>
% include('footer.tpl')
