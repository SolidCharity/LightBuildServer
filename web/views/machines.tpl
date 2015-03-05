% include('header.tpl', title='Machines', page='machines')
    <div class="container">
      <div class="row">
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
	<h2>Planned Jobs</h2>
	<ul>
		% for job in jobs:
		<li>{{job[0]}}-{{job[1]}}-{{job[2]}}-{{job[3]}}-{{job[4]}}-{{job[5]}}</li>
		% end
	</ul>
	<h2>Recent Jobs</h2>
	<table class="table">
		% for job in finishedjobs:
		<tr>
			<td>{{job[8]}}</td>
			<td>
				<a href="/package/{{job[0]}}/{{job[1]}}/{{job[2]}}#{{job[3]}}_{{job[4]}}/{{job[5]}}/{{job[6]}}">
				{{job[0]}}/{{job[1]}}/{{job[2]}}/{{job[3]}}/{{job[4]}}-{{job[5]}}-{{job[6]}}</a>
			</td>
			<td><a href="/logs/{{job[0]}}/{{job[1]}}/{{job[2]}}/{{job[3]}}/{{job[4]}}/{{job[5]}}/{{job[6]}}/{{job[7]["number"]}}">
				build {{job[7]["number"]}}</a></td>
			<td>
			<code class="{{job[7]["resultcode"]}}">{{"Succeeded" if job[7]["resultcode"] == "success" else "Failure"}}</code></td>
		</tr>
		% end
	</table>
      </div>
    </div>
% include('footer.tpl')
