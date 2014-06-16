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
      </div>
    </div>
% include('footer.tpl')
