function export_hsv_cross(destination)
  inputs=load(fullfile(destination,'cross_inputs.mat'));
  forward=hsv2rgb(inputs.forward); boundaries=hsv2rgb(inputs.boundaries); captured=hsv2rgb(inputs.captured);
  save('-mat7-binary',fullfile(destination,'cross_reference.mat'),'forward','boundaries','captured');
end
