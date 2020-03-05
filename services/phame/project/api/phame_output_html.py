# services/phame/project/api/phame.py
import os
import argparse
import logging
import pandas as pd
from flask import Blueprint, render_template, current_app
from flask_login import current_user

from jinja2 import Environment, BaseLoader


phame_blueprint = Blueprint('phame', __name__, template_folder='templates',
                            static_folder='static')
# PROJECT_DIRECTORY = os.path.join('/phame_api', 'media')
# UPLOAD_DIRECTORY = os.path.join('static', 'uploads')
# PHAME_UPLOAD_DIR = os.path.join('/usr','src','app','static', 'uploads')

logging.basicConfig(filename='api.log', level=logging.DEBUG)

def create_output_html(project, username, directory):
    """
    Displays output from PhaME, including summary statistics, sequence lengths
    and tree output using archeopteryx.js library
    Creates a symlink between PhaME output tree file and static directory in
    flask directory
    :param project: project name
    :param username: optional username of user
    :param directory: optional directory with output files
    :return: renders PhaME output page
    """
    project_dir = os.path.join(directory,
                               username, project)
    workdir = os.path.join(project_dir, 'workdir')
    results_dir = os.path.join(workdir, 'results')
    refdir = os.path.join(project_dir, 'refdir')
    trees_target_dir = os.path.join(os.path.dirname(__file__), 'static',
                                    'trees', username)

    if not os.path.exists(workdir):
        error = {'msg': 'Directory does not exist {0}'.format(workdir)}
        return render_template('error.html', error=error)

    # create output tables
    reads_count = len(
        [fname for fname in os.listdir(refdir) if
         (fname.endswith('.fq') or fname.endswith('.fastq'))])
    contigs_count = len(
        [fname for fname in os.listdir(workdir) if fname.endswith('.contig')])
    full_genome_count = len(
        [fname for fname in os.listdir(refdir) if (
            fname.endswith('.fna') or fname.endswith('.fasta'))])

    output_files_list = [f'{project}_summaryStatistics.txt',
                         f'{project}_coverage.txt',
                         f'{project}_snp_pairwiseMatrix.txt',
                         f'{project}_genome_lengths.txt']

    output_tables_list = []
    titles_list = []
    num_genomes = reads_count + contigs_count + full_genome_count
    try:
        for output_file in output_files_list:
            if os.path.exists(os.path.join(results_dir, 'tables',
                                           output_file)):
                if output_file == f'{project}_summaryStatistics.txt':
                    # run_time = '' if not log_time else log_time[:6]
                    try:
                        stats_df = pd.read_table(os.path.join(results_dir,
                                                              'tables',
                                                              output_file),
                                                 header=None, index_col=0)
                        del stats_df.index.name
                        stats_df.columns = ['']

                        run_summary_df = pd.DataFrame(
                            {'# of genomes analyzed': num_genomes,
                             '# of contigs': contigs_count,
                             '# of reads': reads_count,
                             '# of full genomes': full_genome_count,
                             'reference genome used':
                                 stats_df.loc['Reference used'],
                             'project name': project})
                        output_tables_list.append(run_summary_df.to_html(
                            classes='run_summary'))
                        output_tables_list.append(
                            stats_df.to_html(classes='stats'))
                        titles_list.append('Run Summary')
                        titles_list.append('Summary Statistics')
                    except pd.errors.EmptyDataError as e:
                        logging.debug(f'Error reading summary table: {e}')
                elif output_file == f'{project}_coverage.txt':
                    coverage_df = pd.read_table(os.path.join(results_dir,
                                                             'tables',
                                                             output_file))
                    output_tables_list.append(
                        coverage_df.to_html(classes='coverage'))
                    titles_list.append('Genome Coverage')
                elif output_file == f'{project}_snp_pairwiseMatrix.txt':
                    snp_df = pd.read_table(os.path.join(results_dir, 'tables',
                                                        output_file), sep='\t')
                    snp_df.rename(index=str, columns={'Unnamed: 0': 'Genome'},
                                  inplace=True)
                    snp_df.drop(snp_df.columns[-1], axis=1, inplace=True)
                    snp_df.set_index('Genome', inplace=True)
                    snp_df = \
                        snp_df[list(snp_df.columns)].fillna(0.0).astype(int)
                    output_tables_list.append(
                        snp_df.to_html(classes='snp_pairwiseMatrix',
                                       index=True))
                    titles_list.append('SNP pairwise Matrix')
                elif output_file == f'{project}_genome_lengths.txt':
                    genome_df = pd.read_table(os.path.join(results_dir,
                                                           'tables',
                                                           output_file))
                    output_tables_list.append(
                        genome_df.to_html(classes='genome_lengths',
                                          index=False))
                    titles_list.append('Genome Length')

        # Prepare tree files -- create symlinks between tree files in output
        # directory and flask static directory
        if not os.path.exists(trees_target_dir):
            os.makedirs(trees_target_dir)
        # logging.debug(f'tree directory:{trees_target_dir}')
        tree_file_list = [
            fname for fname in os.listdir(os.path.join(results_dir, 'trees'))
            if fname.endswith(
                '.fasttree') or fname.endswith(
                '.treefile'
            ) or 'bestTree' in fname or 'bipartitions' in fname]

        reports_dir = os.path.join(results_dir, 'reports')
        os.makedirs(reports_dir, exist_ok=True)

        static_dir = os.path.join(os.path.dirname(__file__), 'static')

        os.symlink(static_dir, os.path.join(reports_dir, 'static'))
        tree_files = []
        for tree in tree_file_list:
            tree_split = tree.split('/')[-1]
            # target = os.path.join(trees_target_dir, tree_split)
            # tree_files.append(tree_split)
            # logging.debug('fasttree file: trees/{0}'.format(tree_split))
            # source = os.path.join(results_dir, 'trees', tree_split)
            # if not os.path.exists(target):
            #     os.symlink(source, target)
            # if not os.path.exists(target):
            #     error = {'msg': 'File does not exists {0}'.format(target)}
            #     return render_template('error.html', error=error)
            fill_template('templates/script_tree_display.html',
                          dict(username=username,
                               tree=os.path.join('..', 'trees', tree_split), project=project),
                          os.path.join(results_dir,
                                       'reports',
                                       f'{tree_split}.html'))

        logging.debug(f'results dir: {results_dir}/trees/*.fastree')

        fill_template('templates/script_display.html', dict(username=username,
                               tables=output_tables_list,
                               titles=titles_list, tree_files=tree_files,
                               project=project), os.path.join(results_dir,
                                                              'reports',
                                                              'output.html'))

    except Exception as e:
        logging.exception(str(e))


def fill_template(template_file, params_dict, output_file):
    """
    Fill template
    :param template_file: path to template file
    :param params_dict: parameters to fill
    :param output_file: path to output file
    :return:
    """

    with open(template_file, 'r') as fp:
        doc = fp.read()
    t = Environment(loader=BaseLoader()).from_string(doc)
    template_string = t.render(params_dict)
    with open(output_file, 'w') as fp:
        fp.write(template_string)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', help='Directory with project files')
    parser.add_argument('project', help='Name of project')
    parser.add_argument('username', help='username of user that ran project')
    args = vars((parser.parse_args()))
    create_output_html(args['project'], username=args['username'], directory=args['directory'])
