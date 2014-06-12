<html>
<head><title>List available projects</title>
<body>
	<div style="text-align:center">
        % if username == None:
           <a href="/login">Login</a>
        % end
        % if not username == None:
           <a href="/logout">Logout</a>
        % end
	</div>
	<h2>Projects</h2>
	<ul>
             % for project in projects:
		<li>Project {{project}}
                <ul>
                   % for package in projects[project]:
                        <li><a href="{{projects[project][package]['detailurl']}}">Package {{package}}</a>: Build on: 
                        % for buildtarget in projects[project][package]['Distros']:
                             <a href="{{projects[project][package]['buildurl']}}/{{buildtarget}}">{{buildtarget}}</a> 
                        % end
                        </li>
                   % end
                </ul>
		</li>
             % end
	</ul>
        <h2>Build Machines</h2>
        <ul>
            % for buildmachine in buildmachines:
              <li>Container {{buildmachine}}: {{buildmachines[buildmachine]}} <br/>
		&nbsp; &nbsp; Action: <ul>
			<li><a href="/machines/reset/{{buildmachine}}">Reset the machine</a> (This will stop any running jobs on this machine)</li>
		</ul>
                <br/>
              </li>
           % end
        </ul>
</body>
</html>
