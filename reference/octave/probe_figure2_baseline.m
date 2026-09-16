function probe_figure2_baseline(toolbox, samples, destination)
  % External read-only baseline probe. No histogram matching is performed.
  pkg load image;
  addpath(toolbox);
  histograms=zeros(256,3); statistics=zeros(3,2);
  common_histograms=zeros(256,3); common_statistics=zeros(3,2);
  decoded_unequal=zeros(3,1);
  for k=1:3
    a=imread(fullfile(samples,sprintf('cat%d.jpg',k)));
    common=imread(fullfile(destination,sprintf('decoded_cat%d.png',k)));
    decoded_unequal(k)=nnz(a!=common);
    hsv=rgb2hsv(a); v=lum2scale(hsv(:,:,3),1);
    histograms(:,k)=imhist(v); statistics(k,:)=[mean2(v),std2(v)];
    hsv=rgb2hsv(common); v=lum2scale(hsv(:,:,3),1);
    common_histograms(:,k)=imhist(v); common_statistics(k,:)=[mean2(v),std2(v)];
  end
  octave_version=version();
  save('-mat7-binary',fullfile(destination,'octave_baseline.mat'), ...
    'histograms','statistics','common_histograms','common_statistics', ...
    'decoded_unequal','octave_version');
end
