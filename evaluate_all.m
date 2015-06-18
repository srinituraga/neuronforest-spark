for expt = {'linA'}
    dir1 = ['mnt/predictions/' expt{1} '/predictions'];
    %dir1 = ['pyscripts/testData
    files1 = dir(dir1);
    for i = 3:length(files1)
        partial = files1(i).name;
        dir2 = [dir1 '/' partial];
        trainortest = 'test';
        root = [dir2 '/' trainortest];
        sets = dir(root);
        fprintf('\nExperiment: %s\n', root);
        for j=3:length(sets)
            set = [root '/' sets(j).name];
            rots = dir(set);
            for k=3:length(rots)
                rot = [set '/' rots(k).name '/0/split_222'];
                splits = dir(rot);
                a = {};
                for l=3:length(splits)
                    if(splits(l).isdir)
                        a = [a [rot '/' splits(l).name]];
                        description = fileread([rot '/' splits(l).name '/description.txt']);
                    end
                end
            end
            
        end
        dims = get_dimensions(a);
        a
        evaluate_predictions(a, dims, description)
    end
end


%{
rot = 'pyscripts/testData';
splits = dir(rot);
a = {};
for l=3:length(splits)
    if(splits(l).isdir)
        a = [a [rot '/' splits(l).name]];
        description = fileread([rot '/' splits(l).name '/description.txt']);
    end
end
dims = get_dimensions(a);
evaluate_predictions(rot, a, dims, description)
%}