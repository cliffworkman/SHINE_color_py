function export_figure2_common(toolbox, source, destination)
  % Original toolbox calls only; no seeded ties, rewritten matching or JPEG I/O.
  pkg load image;
  addpath(toolbox);
  input=load(source); rgb=input.rgb;
  pre=cell(1,3);
  for k=1:3
    hsv=rgb2hsv(rgb{k}); pre{k}=lum2scale(hsv(:,:,3),1);
  end
  target=avgHist(pre);
  post=processImage(pre,2,1,[],[],0,1);
  pre_hist=zeros(256,3); post_hist=zeros(256,3);
  pre_stats=zeros(3,2); post_stats=zeros(3,2); sorted_post=cell(1,3);
  for k=1:3
    pre_hist(:,k)=imhist(pre{k}); post_hist(:,k)=imhist(post{k});
    pre_stats(k,:)=[mean2(pre{k}),std2(pre{k})];
    post_stats(k,:)=[mean2(post{k}),std2(post{k})];
    sorted_post{k}=sort(post{k}(:));
  end
  octave_version=version();
  delegates=struct('histMatch',which('histMatch'),'avgHist',which('avgHist'), ...
    'processImage',which('processImage'),'rgb2hsv',which('rgb2hsv'));
  assert(strcmpi(delegates.histMatch,fullfile(toolbox,'histMatch.m')));
  save('-mat7-binary',destination,'pre_hist','post_hist','target', ...
    'pre_stats','post_stats','sorted_post','octave_version','delegates');
end
