function export_figure2_jpeg(toolbox, samples, destination)
  % Optional natural-use 0.0.6 path: Octave decodes the supplied JPEGs.
  pkg load image;
  addpath(toolbox);
  pre=cell(1,3);
  for k=1:3
    rgb=imread(fullfile(samples,sprintf('cat%d.jpg',k)));
    hsv=rgb2hsv(rgb); pre{k}=lum2scale(hsv(:,:,3),1);
  end
  post=processImage(pre,2,1,[],[],0,1);
  pre_hist=zeros(256,3); post_hist=zeros(256,3);
  pre_stats=zeros(3,2); post_stats=zeros(3,2);
  for k=1:3
    pre_hist(:,k)=imhist(pre{k}); post_hist(:,k)=imhist(post{k});
    pre_stats(k,:)=[mean2(pre{k}),std2(pre{k})];
    post_stats(k,:)=[mean2(post{k}),std2(post{k})];
  end
  octave_version=version();
  save('-mat7-binary',destination,'pre_hist','post_hist','pre_stats', ...
       'post_stats','octave_version');
end
