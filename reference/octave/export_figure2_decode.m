function export_figure2_decode(samples, destination)
  % Decode each JPEG once, preserving exact uint8 arrays in a lossless MAT file.
  pkg load image;
  rgb=cell(1,3);
  for k=1:3
    rgb{k}=imread(fullfile(samples,sprintf('cat%d.jpg',k)));
    assert(isa(rgb{k},'uint8'));
  end
  octave_version=version();
  save('-mat7-binary',destination,'rgb','octave_version');
end
