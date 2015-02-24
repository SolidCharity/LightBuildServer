% include('header.tpl', title=username+":"+projectname+":"+packagename+" Details", page='package', username=username)
    <div class="container">
      <div class="row">
	<h2>Details of Package {{username}}:{{projectname}}:{{packagename}}</h2>
	<ul>
		<li><a href="{{package['giturl']}}" target="_blank">Project sources</a></li>
		% for branchname in sorted(package['Branches']):
			% for buildtarget in sorted(package['Distros']):
                        % if len(package['Branches']) > 1:
				<a name="{{branchname}}_{{buildtarget}}"></a><br/><br/><br/>
				<a href="#{{branchname}}_{{buildtarget}}">
					<h4>{{branchname}} - {{buildtarget}}</h4>
				</a>
			% end
                        % if len(package['Branches']) == 1:
				<a name="{{buildtarget}}"></a>
				<a href="#{{buildtarget}}">
					<h4>{{buildtarget}}</h4>
				</a>
			% end
			<ul>
                		<li><a href="{{package['buildurl']}}/{{branchname}}/{{buildtarget}}">Trigger build</a></li>
				<li><a href="/livelog/{{username}}/{{projectname}}/{{packagename}}/{{branchname}}/{{buildtarget}}">view current build</a></li>
				<li>Build history and logs:<ul>
					% for buildnumber in package['logs'][buildtarget+"-"+branchname]:
					<li class="{{package['logs'][buildtarget+"-"+branchname][buildnumber]["resultcode"]}}"> 
						<a href="/logs/{{username}}/{{projectname}}/{{packagename}}/{{branchname}}/{{buildtarget}}/{{buildnumber}}">log of build {{buildnumber}}</a> {{package['logs'][buildtarget+"-"+branchname][buildnumber]["timefinished"]}}
						&nbsp;
						{{"Succeeded" if package['logs'][buildtarget+"-"+branchname][buildnumber]["resultcode"] == "success" else "Failure"}}
					</li>
					% end	
				</ul></li>
				<li>Installation instructions:
				<pre>{{package['repoinstructions'][buildtarget]}}</pre>
				</li>
			</ul>
			%end
              	% end
	</ul>
      </div>
    </div>
% include('footer.tpl')
