#!/opt/anaconda/bin/python
"""Create dashboard for IAAS data

Use --help, -h for a help menu.

$Id: $
"""

import sys
#if sys.version_info <= (2, 5):
#    print "This script requires python 2.6 or greater"
#    sys.exit(1)

import logging
# Module level logger
logger = logging.getLogger(__name__)

#import pwd
import os
import os.path
import socket
#import datetime
#import re

import pandas
from bokeh.plotting import figure
from bokeh.models import Plot, ColumnDataSource, Range1d

from bokeh.properties import Instance, Datetime
from bokeh.server.app import bokeh_app
from bokeh.server.utils.plugins import object_page
from bokeh.models.widgets import HBox, DatePicker, VBox, VBoxForm

from flask import request

# Program info
prog = {'name': os.path.basename(sys.argv[0]),
        'dirname': os.path.dirname(sys.argv[0])}
prog['basename'] = os.path.splitext(prog['name'])[0]
prog['pid'] = os.getpid()
#prog['whoami'] = pwd.getpwuid(os.getuid())[0]
prog['hostname'] = socket.gethostname()
prog['datadir'] = '.'

def get_cloudname():
    '''Get cloudname from request'''

    logger.debug('get_cloudname(): Entered')

    name = request.args.get('cloudname', '')
    if not name:
        raise ValueError('Failed to get cloudname')

    logger.info('Request for cloudname %s', name)
    return name

def get_smoketests_data(cloudname):
    '''Get smoketests data for cloud [cloudname] from CSV file

    Args:
        cloudname: string for the nme of the cloud

    Returns:
        A DataFrame with the data
        None if the CSV files for cloudname were not found
    '''

    logger.debug('get_smoketests_data(): Entered')

    csv_file = os.path.join(prog['datadir'], cloudname + '.current')
    logger.info('CSV file for smoketests data will be %s', csv_file)
    if not os.path.isfile(csv_file):
        logger.error('No CSV file for cloudname %s', cloudname)
        return None

    try:
        df = pandas.read_csv(
            csv_file,
            usecols=[0,2,3,4,5],
            parse_dates=['Date']
        ).sort(columns=['Date'])
    except:
        raise ValueError('Failed to get data from CSV file %s' % csv_file)
    
    return df

class DashboardApp(HBox):
    '''The class to instantiate the app'''

    extra_generated_classes = [['DashboardApp', 'DashboardApp', 'HBox']]


    source = Instance(ColumnDataSource)

    datetime_min = Datetime()
    datetime_max = Datetime()

    date_picker_lower = Instance(DatePicker)
    date_picker_upper = Instance(DatePicker)

    smoketests_run_time_plot = Instance(Plot)
    smoketests_results_plot = Instance(Plot)

    layout_column_inputs = Instance(VBoxForm)
    layout_column_smoketests = Instance(VBox)

    # def __init__(self, *args, **kwargs):
    #     logger.debug('DashboardApp.__init__(): Entered')
    #     super(DashboardApp, self).__init__(*args, **kwargs)
    #     self._dfs = {}

    @classmethod
    def create(cls, cloudname, smoketests_data):
        '''
        This function is called once, and is responsible for
        creating all objects (plots, datasources, etc)
        '''
        logger.debug('DashboardApp.create(): Entered')

        obj = cls()
        obj.make_source(smoketests_data)
        obj.set_dates()
        obj.make_date_pickers()
        obj.make_smoketests_run_time_plot()
        obj.make_smoketests_results_plot()
        obj.layout_column_inputs = VBoxForm()
        obj.layout_column_smoketests = VBox()
        obj.make_children()
        return obj

    def make_source(self, smoketests_data):
        logger.debug('DashboardApp.make_source(): Entered')

        #self.source = ColumnDataSource(data=smoketests_data)
        self.source = ColumnDataSource(
            data=dict(
                datetime=smoketests_data['Date'].tolist(),
                runtime=smoketests_data['Run Time'].tolist(),
                numtests=smoketests_data['Tests'].tolist(),
                numfailed=smoketests_data['Failed'].tolist(),
                numskipped=smoketests_data['Skipped'].tolist(),
            )
        )

    def set_dates(self):
        logger.debug('DashboardApp.set_dates(): Entered')

        self.datetime_min = self.source.data['datetime'][0]
        logger.debug('datetime_min=%s', self.datetime_min)
        self.datetime_max = self.source.data['datetime'][-1]
        logger.debug('datetime_max=%s', self.datetime_max)

    def make_date_pickers(self):
        logger.debug('DashboardApp.make_date_pickers(): Entered')

        min = self.datetime_min.date()
        max = self.datetime_max.date()
        self.date_picker_lower = DatePicker(
            value=min,
            min_date=min,
            max_date=max,
        )
        self.date_picker_upper = DatePicker(
            value=max,
            min_date=min,
            max_date=max,
        )

    def make_smoketests_run_time_plot(self):
        logger.debug('DashboardApp.make_smoketests_run_time_plot(): Entered')

        f = figure(
            title=None,
            plot_width=400, plot_height=400,
            x_axis_type='datetime',
            x_range=Range1d(
                start=self.datetime_min,
                end=self.datetime_max
            )
        )
        f.line(
            'datetime', 'runtime', source=self.source,
            line_width=3,
            line_alpha=0.6,
            color='black',
            legend='Run time',
        )
        self.smoketests_run_time_plot = f

    def make_smoketests_results_plot(self):
        logger.debug('DashboardApp.make_smoketests_results_plot(): Entered')

        f = figure(
            title=None,
            x_axis_type='datetime',
            x_range=Range1d(
                start=self.datetime_min,
                end=self.datetime_max
            )
        )
        f.line(
            'datetime', 'numtests', source=self.source,
            color='blue',
            legend='Number of tests',
        )
        f.line(
            'datetime', 'numfailed', source=self.source,
            color='red',
            legend='Tests failed',
        )
        f.line(
            'datetime', 'numskipped', source=self.source,
            color='yellow',
            legend='Tests skipped',
        )
        self.smoketests_results_plot = f

    def make_children(self):
        logger.debug('DashboardApp.make_children(): Entered')

        self.layout_column_inputs.children = [
            self.date_picker_lower, 
            self.date_picker_upper
        ]
        self.layout_column_smoketests.children = [
            self.smoketests_run_time_plot, 
            self.smoketests_results_plot
        ]

    def setup_events(self):
        logger.debug('DashboardApp.setup_events(): Entered')

        super(DashboardApp, self).setup_events()
        if self.datetime_min is None or self.datetime_max is None:
            return
        # for w in ['date_picker_lower', 'date_picker_upper']:
        #     getattr(self, w).on_change('value', self, 'date_change')
        if self.date_picker_lower:
            self.date_picker_lower.on_change('value', self, 'date_change')
        if self.date_picker_upper:
            self.date_picker_lower.on_change('value', self, 'date_change')

    def date_change(self, obj, attrname, old, new):
        '''
        This callback is executed whenever the input form changes. It is
        responsible for updating the plot, or anything else you want.
        The signature is:

        Args:
            obj : the object that changed
            attrname : the attr that changed
            old : old value of attr
            new : new value of attr

        '''
        logger.debug('DashboardApp.date_change(): Entered')

        logger.debug('date_picker_lower.value=%s,date_picker_upper.value=%s',
            self.date_picker_lower.value,
            self.date_picker_upper.value,
        )
        self.smoketests_run_time_plot.x_range = Range1d(
            self.date_picker_lower.value,
            self.date_picker_upper.value
        )

@bokeh_app.route('/dashboard/')
@object_page('Dashboard')
def make_object():
    cloudname = get_cloudname()
    df = get_smoketests_data(cloudname)
    app = DashboardApp.create(cloudname, df)
    return app
