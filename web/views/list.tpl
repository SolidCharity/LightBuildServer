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
             % for project in sorted(projects):
		<li>Project {{project}}
                <ul>
                   % for package in sorted(projects[project]):
                        <li><a href="{{projects[project][package]['detailurl']}}">Package {{package}}</a>: Build on: 
                        % for buildtarget in sorted(projects[project][package]['Distros']):
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
            % for buildmachine in sorted(buildmachines):
              <li>Container {{buildmachine}}: 
		% if buildmachines[buildmachine][0] == "building":
                  {{buildmachines[buildmachine][0]}} <br/>
		  Currently building {{buildmachines[buildmachine][1]}}: <a href="/livelog/{{buildmachines[buildmachine][1]}}">View live log</a><br/>
                % end
                % if not buildmachines[buildmachine][0] == "building": 
                   {{buildmachines[buildmachine]}} <br/>
		% end

		&nbsp; &nbsp; Action: <ul>
			<li><a href="/machines/reset/{{buildmachine}}">Reset the machine</a> (This will stop any running jobs on this machine)</li>
		</ul>
                <br/>
              </li>
           % end
        </ul>
</body>
</html>
