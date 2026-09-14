function probe_edge_cases(toolbox, destination)
  % Empirical probe: call the reference, never substitute an implementation.
  addpath(toolbox);
  cases = struct([]);
  targets = {42, [10 90 200]};
  for k = 1:numel(targets)
    target = targets{k};
    record = struct('source', 17, 'target', target);
    lastwarn('');
    try
      step = (numel(target)-1)/(1-1);
      indices = round(1:step:numel(target));
      [record.expression_warning, record.expression_warning_id] = lastwarn();
      record.step = mat2str(step);
      record.indices = mat2str(indices);
      record.expression_error = '';
    catch err
      record.expression_error = err.message;
      [record.expression_warning, record.expression_warning_id] = lastwarn();
    end
    lastwarn('');
    try
      result = match(uint8(17), target);
      record.output = mat2str(result);
      record.output_shape = size(result);
      record.match_error = '';
    catch err
      record.match_error = err.message;
      record.output = '';
      record.output_shape = [];
    end
    [record.match_warning, record.match_warning_id] = lastwarn();
    cases(k) = record;
  end
  fid = fopen(fullfile(destination, 'single_pixel.json'), 'w');
  fprintf(fid, '%s\n', jsonencode(cases));
  fclose(fid);
end
