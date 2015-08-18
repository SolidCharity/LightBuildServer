% include('header.tpl', title='Machines', page='machines')
    <div class="container">
      <div class="row">
        <h2>Build Machines</h2>
        <ul>
            % for buildmachine in sorted(buildmachines):
              <li>Container {{buildmachine}}: 
		% if buildmachines[buildmachine]["status"] == "BUILDING":
                  % job = buildmachines[buildmachine]["buildjob"].split('/')
                  {{buildmachines[buildmachine]["status"]}} <br/>
		  Currently building
			<a href="/package/{{job[0]}}/{{job[1]}}/{{job[2]}}#{{job[3]}}_{{job[4]}}/{{job[5]}}/{{job[6]}}">
			{{buildmachines[buildmachine]["buildjob"]}}</a>:
			<a href="/livelog/{{buildmachines[buildmachine]["buildjob"]}}">View live log</a><br/>
                % end
                % if not buildmachines[buildmachine]["status"] == "BUILDING": 
                   {{buildmachines[buildmachine]["status"]}} <br/>
		% end

		&nbsp; &nbsp; Action: <ul>
			<li><a href="/machines/reset/{{buildmachine}}">Reset the machine</a> (This will stop any running jobs on this machine)</li>
		</ul>
                <br/>
              </li>
           % end
        </ul>
	<h2>Planned Jobs</h2>
	<ul>
		% for job in jobs:
		<li>
			<a href="/package/{{job["username"]}}/{{job["projectname"]}}/{{job["packagename"]}}#{{job["branchname"]}}_{{job["distro"]}}/{{job["release"]}}/{{job["arch"]}}">
				{{job["username"]}}/{{job["projectname"]}}/{{job["packagename"]}}/{{job["branchname"]}}/{{job["distro"]}}-{{job["release"]}}-{{job["arch"]}}</a>:
			<a href="/cancelplannedbuild/{{job["username"]}}/{{job["projectname"]}}/{{job["packagename"]}}/{{job["branchname"]}}/{{job["distro"]}}/{{job["release"]}}/{{job["arch"]}}">
				Cancel this build</a>
		</li>
		% end
	</ul>
	<h2>Recent Jobs</h2>
	<table class="table">
		% for job in finishedjobs:
		<tr>
			<td>{{job["finished"]}}</td>
			<td>
				<a href="/package/{{job["username"]}}/{{job["projectname"]}}/{{job["packagename"]}}#{{job["branchname"]}}_{{job["distro"]}}/{{job["release"]}}/{{job["arch"]}}">
				{{job["username"]}}/{{job["projectname"]}}/{{job["packagename"]}}/{{job["branchname"]}}/{{job["distro"]}}-{{job["release"]}}-{{job["arch"]}}</a>
			</td>
			<td><a href="/logs/{{job["username"]}}/{{job["projectname"]}}/{{job["packagename"]}}/{{job["branchname"]}}/{{job["distro"]}}/{{job["release"]}}/{{job["arch"]}}/{{job["buildnumber"]}}">
				build {{job["buildnumber"]}}</a></td>
			<td>
			<code class="{{job["buildsuccess"]}}">{{"Succeeded" if job["buildsuccess"] == "success" else "Failure"}}</code></td>
		</tr>
		% end
	</table>
      </div>
    </div>
% include('footer.tpl')
