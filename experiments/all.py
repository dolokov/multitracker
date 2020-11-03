from multitracker.experiments import experiment_a, experiment_b, experiment_c, experiment_d


def all_experiments(args):
    max_steps = 15000 
    experiment_a.experiment_a(args,max_steps)
    experiment_b.experiment_b(args,max_steps)
    experiment_c.experiment_c(args,max_steps)
    experiment_d.experiment_d(args,max_steps)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_id',required=False,type=int)
    parser.add_argument('--video_id',required=False,type=int)
    args = parser.parse_args()
    all_experiments(args)