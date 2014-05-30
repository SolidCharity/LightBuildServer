<html>
<head><title>List available projects</title>
<body>
	<h2>Projects</h2>
	<ul>
             % for project in projects:
		<li>Project {{project}}
                <ul>
                   % for package in projects[project]:
                        <li><a href="{{projects[project][package]['giturl']}}" target="_blank">Package {{package}}</a>: Build on: 
                        % for buildtarget in projects[project][package]['Distros']:
                             <a href="{{projects[project][package]['buildurl']}}/{{buildtarget}}">{{buildtarget}}</a> 
                        % end
                        </li>
                   % end
                </ul>
		</li>
             % end
	</ul>
</body>
</html>
