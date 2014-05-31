<html>
<head><title>LightBuildServer: {{username}}:{{projectname}}:{{packagename}} Details</title>
<body>
        <a href="/">Home</a>
	<h2>Details for {{username}}:{{projectname}}:{{packagename}}</h2>
	<ul>
		<li><a href="{{package['giturl']}}" target="_blank">Project sources</a></li>
		% for buildtarget in package['Distros']:
			<h4>{{buildtarget}}</h4>
			<ul>
                		<li><a href="{{package['buildurl']}}/{{buildtarget}}">Trigger build</a></li>
				<li>TODO view current build</li>
				<li>TODO build history</li>
				<li>TODO Install instructions</li>
			</ul>
              	% end
	</ul>
</body>
</html>
