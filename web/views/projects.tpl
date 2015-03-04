% include('header.tpl', title='Projects', page='projects')
    <div class="container">
      <div class="row">
	% countAccordion = 0
	% countProject = 0
        % for username in sorted(users):
		% countAccordion = countAccordion + 1
		<h2>Projects of user {{username}}</h2>
		<div class="panel-group" id="accordion-{{countAccordion}}">
	             % for project in sorted(users[username]):
			% countProject = countProject + 1
			<div class="panel panel-default">
			<div class="panel-heading" role="tab" id="heading-{{countProject}}">
			<h4 class="panel-title">
				<a data-toggle="collapse" data-parent="#accordion-{{countAccordion}}" href="#collapse-{{countProject}}">{{project}}</a>
			</h4>
			</div>
			<div id="collapse-{{countProject}}" class="panel-collapse collapse" role="tabpanel" aria-labelledby="heading-{{countProject}}">
			<div class="panel-body">
			<a href="/project/{{username}}/{{project}}">Go to Project {{project}}</a>
                	<ul>
	                   % for package in sorted(users[username][project]):
        	                <li><a href="{{users[username][project][package]['packageurl']}}">Package {{package}}</a></li>
                	   % end
	                </ul>
			</div>
			</div>
			</div>
	             % end
		</div>
	% end
      </div>
    </div>
% include('footer.tpl')
