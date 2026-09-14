function probe_rescale_extrema(toolbox, destination)
  % Runtime observations plus calls to unmodified public SHINE rescale.
  addpath(toolbox);
  if ~exist(destination,'dir'), mkdir(destination); end
  finite = [0 10;20 30];
  names = {'finite','partial_nan','all_nan','positive_inf','negative_inf', ...
    'both_infinities','nan_member','partial_nan_member','nan_column', ...
    'all_nan_set','positive_inf_only','opposing_inf_images'};
  sets = {{finite, finite+40}, {[NaN 10;20 30]}, {NaN(2)}, ...
    {[0 Inf;20 30]}, {[0 -Inf;20 30]}, {[-Inf Inf;20 30]}, ...
    {NaN(2),finite,finite+40}, {[NaN 10;20 30],finite+40}, ...
    {[NaN 10;NaN 30],finite+40}, {NaN(2),NaN(2)}, ...
    {Inf(2),finite}, {Inf(2),-Inf(2),finite}};
  % Warm function parsing before capturing execution warnings.
  rescale({finite},1);
  cases = cell(1,numel(names));
  for k = 1:numel(names)
    inputs = sets{k};
    lastwarn('');
    brightests = cellfun(@(a) max(max(a)),inputs);
    darkests = cellfun(@(a) min(min(a)),inputs);
    extrema = [max(brightests),min(darkests),mean(brightests),mean(darkests)];
    [extrema_warning,extrema_warning_id] = lastwarn();
    outputs = cell(1,2); warnings = cell(1,2); warning_ids = cell(1,2); errors = cell(1,2);
    for option = 1:2
      lastwarn(''); errors{option} = '';
      try
        outputs{option} = rescale(inputs,option);
      catch err
        errors{option} = err.message;
      end
      [warnings{option},warning_ids{option}] = lastwarn();
    end
    cases{k} = struct('name',names{k},'inputs',{inputs},'brightests',brightests, ...
      'darkests',darkests,'extrema',extrema,'extrema_warning',extrema_warning, ...
      'extrema_warning_id',extrema_warning_id,'outputs',{outputs}, ...
      'warnings',{warnings},'warning_ids',{warning_ids},'errors',{errors});
  end
  save('-mat7-binary',fullfile(destination,'rescale_extrema.mat'),'cases');
  manifest = struct('octave',version(),'platform',computer(), ...
    'reference_commit','870e058fe8bf1e4090baf2401ff0e127d1c0237a', ...
    'generated_utc',strftime('%Y-%m-%dT%H:%M:%SZ',gmtime(time())), ...
    'script','reference/octave/probe_rescale_extrema.m','case_names',{names}, ...
    'extrema_order',{{'global_max','global_min','mean_max','mean_min'}});
  fid = fopen(fullfile(destination,'extrema_manifest.json'),'w');
  fprintf(fid,'%s\n',jsonencode(manifest)); fclose(fid);
end
