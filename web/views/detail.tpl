<html>
<head><title>LightBuildServer: {{username}}:{{projectname}}:{{packagename}} Details</title>
<body>
        <a href="/">Home</a>
	<h2>Details for {{username}}:{{projectname}}:{{packagename}}</h2>
	<ul>
		<li><a href="{{package['giturl']}}" target="_blank">Project sources</a></li>
		% for buildtarget in sorted(package['Distros']):
			<h4>{{buildtarget}}</h4>
			<ul>
                		<li><a href="{{package['buildurl']}}/{{buildtarget}}">Trigger build</a></li>
				<li><a href="/livelog/{{username}}/{{projectname}}/{{packagename}}/{{buildtarget}}">view current build</a></li>
				<li>Build history and logs:<ul>
					% for buildnumber in package['logs'][buildtarget]:
					<li><a href="/logs/{{username}}/{{projectname}}/{{packagename}}/{{buildtarget}}/{{buildnumber}}">log of build {{buildnumber}}</a> {{package['logs'][buildtarget][buildnumber]}}</li>
					% end	
				</ul></li>
				<li>Installation instructions:
				<pre>{{package['repoinstructions'][buildtarget]}}</pre>
				</li>
			</ul>
              	% end
	</ul>
</body>
</html>
