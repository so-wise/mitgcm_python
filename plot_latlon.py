#######################################################
# Lat-lon shaded plots
#######################################################

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import sys
import numpy as np

from grid import Grid, choose_grid
from file_io import read_netcdf, find_variable, netcdf_time, check_single_time
from utils import convert_ismr, mask_except_ice, mask_3d, mask_land_ice, mask_land, select_bottom, select_year, var_min_max, real_dir
from plot_utils.windows import set_panels, finished_plot
from plot_utils.labels import latlon_axes, check_date_string, parse_date
from plot_utils.colours import set_colours, get_extend
from plot_utils.latlon import cell_boundaries, shade_land, shade_land_ice, contour_iceshelf_front, prepare_vel, overlay_vectors, shade_background, clear_ocean
from diagnostics import t_minus_tf, find_aice_min_max, potential_density
from constants import deg_string, sec_per_year
from calculus import vertical_average


# Basic lat-lon plot of any variable.

# Arguments:
# data: 2D (lat x lon) array of data to plot, already masked as desired
# grid: Grid object

# Optional keyword arguments:
# ax: To make a plot within a larger figure, pass an Axes object to this argument. The image (output of pcolormesh) will then be returned. Otherwise, a new figure with just one subplot will be created.
# gtype: as in function Grid.get_lon_lat
# include_shelf: if True (default), plot the values beneath the ice shelf and contour the ice shelf front. If False, shade the ice shelf in grey like land.
# make_cbar: whether to make a colourbar (default True). 
# ctype: as in function set_colours
# vmin, vmax: as in function set_colours
# zoom_fris: as in function latlon_axes
# xmin, xmax, ymin, ymax: as in function latlon_axes or pster_axes, depending on value of pster (see below).
# pster: plot polar stereographic projection instead of regular lat/lon (default False).
# fill_gap: if pster=True, fill any missing bits of plot with land (default True)
# lon_lines, lat_lines: if pster=True, longitude and/or latitude values to overlay with dotted lines. 
# date_string: something to write on the bottom of the plot about the date
# title: a title to add to the plot
# titlesize: font size for title
# return_fig: if True, return the figure and axis variables so that more work can be done on the plot (eg adding titles). Default False.
# fig_name: as in function finished_plot
# change_points: only matters if ctype='ismr'. As in function set_colours.
# extend: 'neither', 'min', 'max', 'both', or None (will be determined automatically based on vmin and vmax)
# label_latlon: whether to label latitude and longitude axes
# figsize: (width, height) of figure in inches.

def latlon_plot (data, grid, ax=None, gtype='t', include_shelf=True, make_cbar=True, ctype='basic', vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, pster=False, lon_lines=None, lat_lines=None, fill_gap=True, date_string=None, title=None, titlesize=18, return_fig=False, fig_name=None, change_points=None, extend=None, label_latlon=True, figsize=(8,6)):
    
    # Choose what the endpoints of the colourbar should do
    if extend is None:
        extend = get_extend(vmin=vmin, vmax=vmax)

    # If we're zooming, we need to choose the correct colour bounds
    if zoom_fris or any([xmin, xmax, ymin, ymax]):
        vmin_tmp, vmax_tmp = var_min_max(data, grid, pster=pster, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, gtype=gtype)
        # Don't override manually set bounds
        if vmin is None:
            vmin = vmin_tmp
        if vmax is None:
            vmax = vmax_tmp
    # Get colourmap
    cmap, vmin, vmax = set_colours(data, ctype=ctype, vmin=vmin, vmax=vmax, change_points=change_points)

    # Prepare quadrilateral patches
    x, y, data_plot = cell_boundaries(data, grid, gtype=gtype, pster=pster)

    # Make the figure and axes, if needed
    existing_ax = ax is not None
    if not existing_ax:
        fig, ax = plt.subplots(figsize=figsize)

    if pster and fill_gap:
        # Shade the background in grey
        shade_background(ax)
        # Clear the ocean back to white
        clear_ocean(ax, grid, gtype=gtype, pster=pster)
    else:
        if include_shelf:
            # Shade land in grey
            shade_land(ax, grid, gtype=gtype, pster=pster)
        else:
            # Shade land and ice shelves in grey
            shade_land_ice(ax, grid, gtype=gtype, pster=pster)
    # Plot the data    
    img = ax.pcolormesh(x, y, data_plot, cmap=cmap, vmin=vmin, vmax=vmax)
    if include_shelf:
        # Contour ice shelf front
        contour_iceshelf_front(ax, grid, pster=pster)
    if make_cbar:
        # Add a colourbar
        plt.colorbar(img, extend=extend)
    # Set axes limits etc.
    latlon_axes(ax, x, y, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, label=label_latlon, pster=pster, lon_lines=lon_lines, lat_lines=lat_lines, grid=grid)
    if date_string is not None and not existing_ax:
        # Add the date in the bottom right corner
        plt.text(.99, .01, date_string, fontsize=14, ha='right', va='bottom', transform=fig.transFigure)
    if title is not None:
        # Add a title
        plt.title(title, fontsize=titlesize)

    if return_fig:
        return fig, ax
    elif existing_ax:
        return img
    else:
        finished_plot(fig, fig_name=fig_name)
        

# Plot ice shelf melt rate field.

# Arguments:
# shifwflx: 2D (lat x lon) array of ice shelf freshwater flux (variable SHIfwFlx), already masked
# grid: Grid object

# Optional keyword arguments:
# vmin, vmax: as in function set_colours
# zoom_fris: as in function latlon_axes
# xmin, xmax, ymin, ymax: as in function latlon_axes
# date_string: as in function latlon_plot
# change_points: as in function set_colours
# fig_name: as in function finished_plot
# figsize: as in function latlon_plot

def plot_ismr (shifwflx, grid, vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, date_string=None, change_points=None, fig_name=None, figsize=(8,6)):

    # Convert to m/y
    ismr = convert_ismr(shifwflx)
    latlon_plot(ismr, grid, ctype='ismr', vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, change_points=change_points, title='Ice shelf melt rate (m/y)', fig_name=fig_name, figsize=figsize)


# Plot bottom water temperature, salinity, or age.

# Arguments:
# var: 'temp', 'salt', or 'age'.
# data: 3D (depth x lat x lon) array of temperature in degC or salinity in psu, already masked with hfac
# grid: Grid object

# Optional keyword arguments:
# vmin, vmax: as in function set_colours
# zoom_fris: as in function latlon_axes
# xmin, xmax, ymin, ymax: as in function latlon_axes
# date_string: as in function latlon_plot
# fig_name: as in function finished_plot
# figsize: as in function latlon_plot

def plot_bw (var, data, grid, vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, date_string=None, fig_name=None, figsize=(8,6)):

    if var == 'temp':
        title = 'Bottom water temperature (' + deg_string + 'C)'
    elif var == 'salt':
        title = 'Bottom water salinity (psu)'
    elif var == 'age':
        title = 'Bottom water age (years)'
    latlon_plot(select_bottom(data), grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, title=title, fig_name=fig_name, figsize=figsize)


# Plot surface temperature or salinity.

# Arguments:
# var: 'temp' or 'salt'
# data: 3D (depth x lat x lon) array of temperature in degC or salinity in psu, already masked with hfac
# grid: Grid object

# Optional keyword arguments:
# vmin, vmax: as in function set_colours
# zoom_fris: as in function latlon_axes
# xmin, xmax, ymin, ymax: as in function latlon_axes
# date_string: as in function latlon_plot
# fig_name: as in function finished_plot
# figsize: as in function latlon_plot

def plot_ss (var, data, grid, vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, date_string=None, fig_name=None, figsize=(8,6)):

    if var == 'temp':
        title = 'Sea surface temperature (' + deg_string + 'C)'
    elif var == 'salt':
        title = 'Sea surface salinity (psu)'
    latlon_plot(data[0,:], grid, include_shelf=False, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, title=title, fig_name=fig_name, figsize=figsize)


# Plot miscellaneous 2D variables that do not include the ice shelf: sea ice concentration or thickness, mixed layer depth, free surface, surface salt flux.

# Arguments:
# var: 'aice', 'hice', 'hsnow', 'mld', 'eta', 'saltflx', 'iceprod'
# data: 2D (lat x lon) array of sea ice concentration (fraction), sea ice thickness, snow thickness, mixed layer depth, free surface (all m), surface salt flux (kg/m^2/s), or sea ice production (m/y) already masked with the land and ice shelf
# grid: Grid object

# Optional keyword arguments:
# ctype: as in function set_colours
# vmin, vmax: as in function set_colours
# zoom_fris: as in function latlon_axes
# xmin, xmax, ymin, ymax: as in function latlon_axes
# date_string: as in function latlon_plot
# fig_name: as in function finished_plot
# figsize: as in function latlon_plot

def plot_2d_noshelf (var, data, grid, ctype='basic', vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, date_string=None, fig_name=None, figsize=(8,6)):

    if var == 'aice':
        title = 'Sea ice concentration (fraction)'
    elif var == 'hice':
        title = 'Sea ice effective thickness (m)'
    elif var == 'hsnow':
        title = 'Snow effective thickness (m)'
    elif var == 'mld':
        title = 'Mixed layer depth (m)'
    elif var == 'eta':
        title = 'Free surface (m)'
    elif var == 'saltflx':
        title = r'Surface salt flux (kg/m$^2$/s)'
    elif var == 'iceprod':
        title = 'Sea ice production (m/y)'
    latlon_plot(data, grid, include_shelf=False, ctype=ctype, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, title=title, fig_name=fig_name, figsize=figsize)


# Plot the difference from the in-situ freezing point.

# Arguments:
# temp, salt: 3D (depth x lat x lon) arrays of temprature and salinity, already masked with hfac
# grid: Grid object

# Optional keyword arguments:
# tf_option: 'bottom' (to plot difference from in-situ freezing point in the bottom layer), 'max' (to plot maximum at each point in the water column), 'min' (to plot minimum, default).
# vmin, vmax: as in function set_colours
# zoom_fris: as in function latlon_axes
# xmin, xmax, ymin, ymax: as in function latlon_axes
# date_string: as in function latlon_plot
# fig_name: as in function finished_plot
# figsize: as in function latlon_plot

def plot_tminustf (temp, salt, grid, tf_option='min', vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, date_string=None, fig_name=None, figsize=(8,6)):

    # Calculate difference from freezing point
    tminustf = t_minus_tf(temp, salt, grid)
    # Do the correct vertical transformation
    if tf_option == 'bottom':
        tmtf_plot = select_bottom(tminustf)
        title_end = '\n(bottom layer)'
    elif tf_option == 'max':
        tmtf_plot = np.amax(tminustf, axis=0)
        title_end = '\n(maximum over depth)'
    elif tf_option == 'min':
        tmtf_plot = np.amin(tminustf, axis=0)
        title_end = '\n(minimum over depth)'
    latlon_plot(tmtf_plot, grid, ctype='plusminus', vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, title=r'Difference from in-situ freezing point ('+deg_string+'C)'+title_end, fig_name=fig_name, figsize=figsize)


# Plot horizontal ocean or sea ice velocity: magnitude overlaid with vectors.

# Arguments:
# u, v: 3D (depth x lat x lon) arrays of u and v, on the u-grid and v-grid respectively, already masked with hfac
# grid: Grid object

# Optional keyword arguments:
# vel_option: as in function prepare_vel
# z0: as in function prepare_vel (only matters if vel_option='interp')
# vmin, vmax: as in function set_colours
# zoom_fris: as in function latlon_axes
# xmin, xmax, ymin, ymax: as in function latlon_axes
# date_string: as in function latlon_plot
# fig_name: as in function finished_plot
# figsize: as in function latlon_plot
# chunk: as in function overlay_vectors

def plot_vel (u, v, grid, vel_option='avg', z0=None, vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, date_string=None, fig_name=None, figsize=(8,6), chunk=None, scale=None):

    # Do the correct vertical transformation, and interpolate to the tracer grid
    speed, u_plot, v_plot = prepare_vel(u, v, grid, vel_option=vel_option, z0=z0)

    include_shelf=True
    if vel_option == 'avg':
        title_beg = 'Vertically averaged '
    elif vel_option == 'sfc':
        title_beg = 'Surface '
    elif vel_option == 'bottom':
        title_beg = 'Bottom '
    elif vel_option == 'ice':
        title_beg = 'Sea ice '
        include_shelf = False
    elif vel_option == 'interp':
        title_beg = str(int(round(-z0)))+'m '

    # Make the plot but don't finish it yet
    fig, ax = latlon_plot(speed, grid, ctype='vel', include_shelf=include_shelf, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, title=title_beg+'velocity (m/s)', return_fig=True, figsize=figsize)

    # Overlay circulation
    if chunk is None:
        if zoom_fris:
            chunk = 6
        else:
            chunk = 10
    if vel_option == 'avg':
        scale = 0.8
    elif vel_option == 'sfc':
        scale = 1.5
    elif vel_option == 'bottom':
        scale = 1
    elif vel_option == 'ice':
        scale = 2
    overlay_vectors(ax, u_plot, v_plot, grid, chunk=chunk, scale=scale)

    finished_plot(fig, fig_name=fig_name)


# Plot horizontal velocity streamfunction (vertically integrated).

# Arguments:
# psi: 3D (depth x lat x lon) array of horizontal velocity streamfunction, already masked with hfac
# Everything else as before.

def plot_psi (psi, grid, vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, date_string=None, fig_name=None, figsize=(8,6)):

    # Vertically integrate and convert to Sv
    psi = np.sum(psi, axis=0)*1e-6
    latlon_plot(psi, grid, ctype='plusminus', vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, title='Horizontal velocity streamfunction (Sv)\nvertically integrated', fig_name=fig_name, figsize=figsize)


# NetCDF interface. Call this function with a specific variable key and information about the necessary NetCDF file, to get a nice lat-lon plot.

# Arguments:
# var: keyword indicating which special variable to plot. The options are:
#      'ismr': ice shelf melt rate
#      'bwtemp': bottom water temperature
#      'bwsalt': bottom water salinity
#      'bwage': bottom water age
#      'sst': surface temperature
#      'sss': surface salinity
#      'aice': sea ice concentration
#      'hice': sea ice thickness
#      'hsnow': snow thickness
#      'mld': mixed layer depth
#      'eta': free surface
#      'saltflx': surface salt flux
#      'tminustf': difference from in-situ freezing point
#      'vel': horizontal velocity: magnitude overlaid with vectors
#      'velice': sea ice velocity: magnitude overlaid with vectors
#      'psi': horizontal velocity streamfunction
#      'iceprod': sea ice production
# file_path: path to NetCDF file containing the necessary variable:
#            'ismr': SHIfwFlx
#            'bwtemp': THETA
#            'bwage': TRAC01 with appropriate edits to the code
#            'bwsalt': SALT
#            'sst': THETA
#            'sss': SALT
#            'aice': SIarea
#            'hice': SIheff
#            'hsnow': SIhsnow
#            'mld': MXLDEPTH
#            'eta': ETAN
#            'saltflx': SIempmr
#            'tminustf': THETA and SALT
#            'vel': UVEL and VVEL
#            'velice': SIuice and SIvice
#            'psi': PsiVEL
#            'iceprod': SIdHbOCN, SIdHbATC, SIdHbATO, SIdHbFLO
#            If there are two variables needed (eg THETA and SALT for 'tminustf') and they are stored in separate files, you can put the other file in second_file_path (see below).

# There are three ways to deal with the Grid object:
# (1) If you have precomputed the grid, pass that object to the keyword argument "grid".
# (2) If you haven't precomputed the grid but file_path contains the grid variables, do nothing. The code will automatically build the grid from file_path.
# (3) If you haven't precomputed the grid and file_path doesn't contain the grid variables, pass the path to either (a) the binary grid directory or (b) a NetCDF file containing the grid variables to the keyword argument "grid".

# Optional keyword arguments:
# grid: as described above
# time_index, t_start, t_end, time_average: as in function read_netcdf. You must either define time_index or set time_average=True, so it collapses to a single record.
# vmin, vmax: as in function set_colours
# zoom_fris: as in function latlon_axes
# xmin, xmax, ymin, ymax: as in function latlon_axes
# date_string: as in function latlon_plot. If time_index is defined and date_string isn't, date_string will be automatically determined based on the calendar in file_path.
# fig_name: as in function finished_plot
# second_file_path: path to NetCDF file containing a second variable which is necessary and not contained in file_path. It doesn't matter which is which.
# change_points: only matters for 'ismr'. As in function set_colours.
# tf_option: only matters for 'tminustf'. As in function plot_tminustf.
# vel_option: only matters for 'vel'. As in function prepare_vel.
# z0: only matters for vel_option='interp'. As in function prepare_vel.
# chunk: only matters for 'vel' or 'velice'. As in function overlay_vectors.
# figsize: as in function latlon_plot

def read_plot_latlon (var, file_path, grid=None, time_index=None, t_start=None, t_end=None, time_average=False, vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, date_string=None, fig_name=None, second_file_path=None, change_points=None, tf_option='min', vel_option='avg', z0=None, chunk=None, scale=None, figsize=(8,6)):

    # Build the grid if needed
    grid = choose_grid(grid, file_path)
    # Make sure we'll end up with a single record in time
    check_single_time(time_index, time_average)
    # Determine what to write about the date
    date_string = check_date_string(date_string, file_path, time_index)

    # Inner function to read a variable from the correct NetCDF file and mask appropriately
    def read_and_mask (var_name, mask_option, check_second=False, gtype='t'):
        # Do we need to choose the right file?
        if check_second and second_file_path is not None:
            file_path_use = find_variable(file_path, second_file_path, var_name)
        else:
            file_path_use = file_path
        # Read the data
        data = read_netcdf(file_path_use, var_name, time_index=time_index, t_start=t_start, t_end=t_end, time_average=time_average)
        # Apply the correct mask
        if mask_option == 'except_ice':
            data = mask_except_ice(data, grid, gtype=gtype)
        elif mask_option == '3d':
            data = mask_3d(data, grid, gtype=gtype)
        elif mask_option == 'land_ice':
            data = mask_land_ice(data, grid, gtype=gtype)
        else:
            print 'Error (read_and_mask): invalid mask_option ' + mask_option
            sys.exit()
        return data

    # Now read and mask the necessary variables
    if var == 'ismr':
        shifwflx = read_and_mask('SHIfwFlx', 'except_ice')
    if var in ['bwtemp', 'sst', 'tminustf']:
        temp = read_and_mask('THETA', '3d', check_second=True)
    if var in ['bwsalt', 'sss', 'tminustf']:
        salt = read_and_mask('SALT', '3d', check_second=True)
    if var == 'bwage':
        age = read_and_mask('TRAC01', '3d')
    if var == 'aice':
        aice = read_and_mask('SIarea', 'land_ice')
    if var == 'hice':
        hice = read_and_mask('SIheff', 'land_ice')
    if var == 'hsnow':
        hsnow = read_and_mask('SIhsnow', 'land_ice')
    if var == 'mld':
        mld = read_and_mask('MXLDEPTH', 'land_ice')
    if var == 'eta':
        eta = read_and_mask('ETAN', 'land_ice')
    if var == 'saltflx':
        saltflx = read_and_mask('SIempmr', 'land_ice')
    if var == 'vel':
        u = read_and_mask('UVEL', '3d', check_second=True, gtype='u')
        v = read_and_mask('VVEL', '3d', check_second=True, gtype='v')
    if var == 'velice':
        uice = read_and_mask('SIuice', 'land_ice', check_second=True, gtype='u')
        vice = read_and_mask('SIvice', 'land_ice', check_second=True, gtype='v')
    if var == 'psi':
        psi = read_and_mask('PsiVEL', '3d')
    if var == 'iceprod':
        iceprod = read_and_mask('SIdHbOCN', 'land_ice', check_second=True) + read_and_mask('SIdHbATC', 'land_ice', check_second=True) + read_and_mask('SIdHbATO', 'land_ice', check_second=True) + read_and_mask('SIdHbFLO', 'land_ice', check_second=True)
        # Convert from m/s to m/y
        iceprod *= sec_per_year
        
    # Plot
    if var == 'ismr':
        plot_ismr(shifwflx, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, change_points=change_points, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'bwtemp':
        plot_bw('temp', temp, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'bwsalt':
        plot_bw('salt', salt, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'bwage':
        plot_bw('age', age, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'sst':
        plot_ss('temp', temp, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'sss':
        plot_ss('salt', salt, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'aice':
        plot_2d_noshelf('aice', aice, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'hice':
        plot_2d_noshelf('hice', hice, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'hsnow':
        plot_2d_noshelf('hsnow', hsnow, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'mld':
        plot_2d_noshelf('mld', mld, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'eta':
        plot_2d_noshelf('eta', eta, grid, ctype='plusminus', vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'saltflx':
        plot_2d_noshelf('saltflx', saltflx, grid, ctype='plusminus', vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'tminustf':
        plot_tminustf(temp, salt, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, tf_option=tf_option, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'vel':
        plot_vel(u, v, grid, vel_option=vel_option, z0=z0, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize, chunk=chunk, scale=scale)
    elif var == 'velice':
        plot_vel(uice, vice, grid, vel_option='ice', vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize, chunk=chunk, scale=scale)
    elif var == 'psi':
        plot_psi(psi, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    elif var == 'iceprod':
        plot_2d_noshelf('iceprod', iceprod, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, fig_name=fig_name, figsize=figsize)
    else:
        print 'Error (read_plot_latlon): variable key ' + str(var) + ' does not exist'
        sys.exit()


# NetCDF interface for difference plots. Given simulations 1 and 2, plot the difference (2 minus 1) for the given variable.

# Arguments are largely the same as read_plot_latlon, here are the exceptions:
# var: as in read_plot_latlon, but options restricted to: 'ismr', 'bwtemp', 'bwsalt', 'bwage', 'sst', 'sss', 'aice', 'hice', 'hsnow', 'mld', 'eta', 'vel', 'velice', 'iceprod'
# file_path_1, file_path_2: paths to NetCDF files containing the necessary variables for simulations 1 and 2; you can use second_file_path_1 and second_file_path_2 keyword arguments if needed (should only be necessary for 'vel' and 'velice').
# It is assumed they cover the same period of time. If they don't, you can set time_index_2, etc. for the corresponding timesteps in file_path_2 which match time_index, etc. for file_path_1.

def read_plot_latlon_diff (var, file_path_1, file_path_2, grid=None, time_index=None, t_start=None, t_end=None, time_average=False, time_index_2=None, t_start_2=None, t_end_2=None, vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, date_string=None, fig_name=None, second_file_path_1=None, second_file_path_2=None, vel_option='avg', z0=None, figsize=(8,6)):

    # Figure out if the two files use different time indices
    diff_time = (time_index_2 is not None) or (time_average and (t_start_2 is not None or t_end_2 is not None))

    # Get set up, just like read_plot_latlon
    grid = choose_grid(grid, file_path_1)
    check_single_time(time_index, time_average)
    date_string = check_date_string(date_string, file_path_1, time_index)

    # Inner function to read a variable from the correct NetCDF file and mask appropriately
    # This is the same as in read_plot_latlon except it requires file path arguments
    def read_and_mask (var_name, mask_option, file_path, second_file_path=None, check_second=False, check_diff_time=False):
        # Do we need to choose the right file?
        if check_second and second_file_path is not None:
            file_path_use = find_variable(file_path, second_file_path, var_name)
        else:
            file_path_use = file_path
        # Read the data
        if check_diff_time and diff_time:
            # It's the second simulation and it has alternate time indices
            data = read_netcdf(file_path_use, var_name, time_index=time_index_2, t_start=t_start_2, t_end=t_end_2, time_average=time_average)
        else:
            data = read_netcdf(file_path_use, var_name, time_index=time_index, t_start=t_start, t_end=t_end, time_average=time_average)
        # Apply the correct mask
        if mask_option == 'except_ice':
            data = mask_except_ice(data, grid)
        elif mask_option == '3d':
            data = mask_3d(data, grid)
        elif mask_option == 'land_ice':
            data = mask_land_ice(data, grid)
        else:
            print 'Error (read_and_mask): invalid mask_option ' + mask_option
            sys.exit()
        return data

    # Interface to call read_and_mask for each variable
    def read_and_mask_both (var_name, mask_option, check_second=False):
        data1 = read_and_mask(var_name, mask_option, file_path_1, second_file_path=second_file_path_1, check_second=check_second)
        data2 = read_and_mask(var_name, mask_option, file_path_2, second_file_path=second_file_path_2, check_second=check_second, check_diff_time=True)
        return data1, data2
        
    # Now read and mask the necessary variables
    if var == 'ismr':
        shifwflx_1, shifwflx_2 = read_and_mask_both('SHIfwFlx', 'except_ice')
    if var in ['bwtemp', 'sst']:
        temp_1, temp_2 = read_and_mask_both('THETA', '3d')
    if var in ['bwsalt', 'sss']:
        salt_1, salt_2 = read_and_mask_both('SALT', '3d')
    if var == 'bwage':
        age_1, age_2 = read_and_mask_both('TRAC01', '3d')
    if var == 'aice':
        aice_1, aice_2 = read_and_mask_both('SIarea', 'land_ice')
    if var == 'hice':
        hice_1, hice_2 = read_and_mask_both('SIheff', 'land_ice')
    if var == 'hsnow':
        hsnow_1, hsnow_2 = read_and_mask_both('SIhsnow', 'land_ice')
    if var == 'mld':
        mld_1, mld_2 = read_and_mask_both('MXLDEPTH', 'land_ice')
    if var == 'eta':
        eta_1, eta_2 = read_and_mask_both('ETAN', 'land_ice')
    if var == 'vel':
        u_1, u_2 = read_and_mask_both('UVEL', '3d', check_second=True)
        v_1, v_2 = read_and_mask_both('VVEL', '3d', check_second=True)
    if var == 'velice':
        uice_1, uice_2 = read_and_mask_both('SIuice', 'land_ice', check_second=True)
        vice_1, vice_2 = read_and_mask_both('SIvice', 'land_ice', check_second=True)
    elif var == 'iceprod':
        iceprod_1a, iceprod_2a = read_and_mask_both('SIdHbOCN', 'land_ice', check_second=True)
        iceprod_1b, iceprod_2b = read_and_mask_both('SIdHbATC', 'land_ice', check_second=True)
        iceprod_1c, iceprod_2c = read_and_mask_both('SIdHbATO', 'land_ice', check_second=True)
        iceprod_1d, iceprod_2d = read_and_mask_both('SIdHbFLO', 'land_ice', check_second=True)
        # Add the terms and convert to m/y
        iceprod_1 = (iceprod_1a + iceprod_1b + iceprod_1c + iceprod_1d)*sec_per_year
        iceprod_2 = (iceprod_2a + iceprod_2b + iceprod_2c + iceprod_2d)*sec_per_year

    # Do necessary conversions and get final difference field; also set title
    if var == 'ismr':
        data_diff = convert_ismr(shifwflx_2 - shifwflx_1)
        title = 'Change in ice shelf melt rate (m/y)'
    elif var == 'bwtemp':
        data_diff = select_bottom(temp_2 - temp_1)
        title = r'Change in bottom water temperature ('+deg_string+'C)'
    elif var == 'bwsalt':
        data_diff = select_bottom(salt_2 - salt_1)
        title = 'Change in bottom water salinity (psu)'
    elif var == 'bwage':
        data_diff = select_bottom(age_2 - age_1)
        title = 'Change in bottom water age (years)'
    elif var == 'sst':
        data_diff = temp_2[0,:] - temp_1[0,:]
        title = r'Change in sea surface temperature ('+deg_string+'C)'
    elif var == 'sss':
        data_diff = salt_2[0,:] - salt_1[0,:]
        title = 'Change in sea surface salinity (psu)'
    elif var == 'aice':
        data_diff = aice_2 - aice_1
        title = 'Change in sea ice concentration (fraction)'
    elif var == 'hice':
        data_diff = hice_2 - hice_1
        title = 'Change in sea ice effective thickness (m)'
    elif var == 'hsnow':
        data_diff = hsnow_2 - hsnow_1
        title = 'Change in snow effective thickness (m)'
    elif var == 'mld':
        data_diff = mld_2 - mld_1
        title = 'Change in mixed layer depth (m)'
    elif var == 'eta':
        data_diff = eta_2 - eta_1
        title = 'Change in free surface (m)'
    elif var == 'vel':
        speed_1 = prepare_vel(u_1, v_1, grid, vel_option=vel_option, z0=z0)[0]
        speed_2 = prepare_vel(u_2, v_2, grid, vel_option=vel_option, z0=z0)[0]
        data_diff = speed_2 - speed_1
        title = 'Change in '
        if vel_option == 'avg':
            title += 'vertically averaged'
        elif vel_option == 'sfc':
            title += 'surface'
        elif vel_option == 'bottom':
            title += 'bottom'
        elif vel_option == 'interp':
            title += str(int(round(-z0))) + 'm'
        title += ' speed (m/s)'
    elif var == 'velice':
        speed_1 = prepare_vel(uice_1, vice_1, grid, vel_option='ice')[0]
        speed_2 = prepare_vel(uice_2, vice_2, grid, vel_option='ice')[0]
        data_diff = speed_2 - speed_1
        title = 'Change in sea ice speed (m/s)'
    elif var == 'iceprod':
        data_diff = iceprod_2 - iceprod_1
        title = 'Change in sea ice production (m/y)'
    else:
        print 'Error (read_plot_latlon_diff): variable key ' + str(var) + ' does not exist'
        sys.exit()

    # Choose value for include_shelf
    if var in ['ismr', 'bwtemp', 'bwsalt', 'bwage', 'vel']:
        include_shelf = True
    elif var in ['sst', 'sss', 'aice', 'hice', 'hsnow', 'mld', 'eta', 'velice', 'iceprod']:
        include_shelf = False

    # Plot
    latlon_plot(data_diff, grid, include_shelf=include_shelf, ctype='plusminus', vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, title=title, fig_name=fig_name, figsize=figsize)    


# Plot topographic variables: bathymetry, ice shelf draft, water column thickness.

# Arguments:
# var: 'bathy', 'draft', 'wct'
# grid: either a Grid object, or the path to the binary grid directory or a NetCDF file containing grid variables

# Optional keyword arguments:
# vmin, vmax: as in function set_colours
# zoom_fris: as in function latlon_axes
# xmin, xmax, ymin, ymax: as in function latlon_axes
# fig_name: as in function finished_plot
# figsize: as in function latlon_plot

def plot_topo (var, grid, vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, fig_name=None, figsize=(8,6)):

    if not isinstance(grid, Grid):
        # Create a Grid object from the given path
        grid = Grid(grid)

    if var == 'bathy':
        data = abs(mask_land(grid.bathy, grid))
        title = 'Bathymetry (m)'
    elif var == 'draft':
        data = abs(mask_except_ice(grid.draft, grid))
        title = 'Ice shelf draft (m)'
    elif var == 'wct':
        data = abs(mask_land(grid.wct, grid))
        title = 'Water column thickness (m)'

    latlon_plot(data, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, title=title, fig_name=fig_name, figsize=figsize)


# Make an empty map just showing land in grey and ice shelf contours in black.
def plot_empty (grid, ax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, fig_name=None, figsize=(8,6)):

    if not isinstance(grid, Grid):
        grid = Grid(grid)

    lon = grid.lon_corners_2d
    lat = grid.lat_corners_2d

    existing_ax = ax is not None
    if not existing_ax:
        fig, ax = plt.subplots(figsize=figsize)
        
    shade_land(ax, grid)
    contour_iceshelf_front(ax, grid)
    latlon_axes(ax, lon, lat, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)
    if not existing_ax:
        finished_plot(fig, fig_name=fig_name)


# 1x2 lat-lon plot showing sea ice area at the timesteps of minimum and maximum area in the given year.
def plot_aice_minmax (file_path, year, grid=None, fig_name=None, monthly=True, figsize=(12,6)):

    # Build the grid if needed
    grid = choose_grid(grid, file_path)

    # Read sea ice area and the corresponding dates
    aice = mask_land_ice(read_netcdf(file_path, 'SIarea'), grid, time_dependent=True)
    time = netcdf_time(file_path, monthly=monthly)
    # Find the range of dates we care about
    t_start, t_end = select_year(time, year)
    # Trim the arrays to these dates
    aice = aice[t_start:t_end,:]
    time = time[t_start:t_end]
    # Find the indices of min and max sea ice area
    t_min, t_max = find_aice_min_max(aice, grid)
    # Wrap up in lists for easy iteration
    aice_minmax = [aice[t_min,:], aice[t_max,:]]
    time_minmax = [time[t_min], time[t_max]]

    # Plot
    fig, gs, cax = set_panels('1x2C1', figsize=figsize)
    for t in range(2):
        ax = plt.subplot(gs[0,t])
        img = latlon_plot(aice_minmax[t], grid, ax=ax, include_shelf=False, vmin=0, vmax=1, title=parse_date(date=time_minmax[t]), make_cbar=False)
        if t == 1:
            # Don't need latitude labels a second time
            ax.set_yticklabels([])
    # Colourbar
    plt.colorbar(img, cax=cax, orientation='horizontal')
    # Main title above
    plt.suptitle('Min and max sea ice area', fontsize=22)
    finished_plot(fig, fig_name=fig_name)


# Basic plot for a domain in progress (see make_domain.py).
# x, y: tile edges (either lat-lon or polar stereographic)
# data: field to plot, at centres of tiles
# title: optional string to put on title
def plot_tmp_domain (x, y, data, title=None, figsize=(8,6)):

    fig, ax = plt.subplots(figsize=figsize)
    img = ax.pcolormesh(x, y, data)
    ax.axis('tight')
    plt.colorbar(img)
    if title is not None:
        plt.title(title, fontsize=18)
    fig.show()


# Plot horizontal resolution (square root of the area of each grid cell).

# Arguments:
# grid: either a Grid object, or the path to the binary grid directory or a NetCDF file containing grid variables

# Optional keyword arguments:
# vmin, vmax: as in function set_colours
# zoom_fris: as in function latlon_axes
# xmin, xmax, ymin, ymax: as in function latlon_axes
# fig_name: as in function finished_plot
# figsize: as in function latlon_plot

def plot_resolution (grid, vmin=None, vmax=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, fig_name=None, figsize=(8,6)):

    if not isinstance(grid, Grid):
        grid = Grid(grid)

    # Resolution is the square root of the area of each cell, converted to km
    # Also apply land mask
    res = mask_land(np.sqrt(grid.dA)*1e-3, grid)

    latlon_plot(res, grid, vmin=vmin, vmax=vmax, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, title='Horizontal resolution (km)', fig_name=fig_name, figsize=figsize)


# Make a 3x1 plot that compares a lat-lon variable from two different simulations: absolute for each simulation, and their anomaly.
def latlon_comparison_plot (data1, data2, grid, gtype='t', include_shelf=False, ctype='basic', vmin=None, vmax=None, vmin_diff=None, vmax_diff=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, date_string=None, title1=None, title2=None, suptitle=None, fig_name=None, change_points=None, extend=None, extend_diff=None, u_1=None, v_1=None, u_2=None, v_2=None, chunk=None, scale=0.8):

    if extend is None:
        extend = get_extend(vmin=vmin, vmax=vmax)
    if extend_diff is None:
        extend_diff = get_extend(vmin=vmin_diff, vmax=vmax_diff)
        
    if zoom_fris:
        chunk = 6
    else:
        chunk = 10

    # Get the bounds
    vmin_1, vmax_1 = var_min_max(data1, grid, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, gtype=gtype)
    vmin_2, vmax_2 = var_min_max(data2, grid, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, gtype=gtype)
    if vmin is None:
        vmin = min(vmin_1, vmin_2)
    if vmax is None:
        vmax = max(vmax_1, vmax_2)

    # Set up the plot
    fig, gs, cax1, cax2 = set_panels('1x3C2')
    # Wrap things up in lists for easier iteration
    data = [data1, data2, data2-data1]
    u = [u_1, u_2, None]
    v = [v_1, v_2, None]
    vmin0 = [vmin, vmin, vmin_diff]
    vmax0 = [vmax, vmax, vmax_diff]
    ctype0 = [ctype, ctype, 'plusminus']
    title = [title1, title2, 'Anomaly']
    cax = [cax1, None, cax2]
    extend0 = [extend, None, extend_diff]
    label_latlon = [True, False, False]
    for i in range(3):
        ax = plt.subplot(gs[0,i])
        img = latlon_plot(data[i], grid, ax=ax, gtype=gtype, include_shelf=include_shelf, make_cbar=False, ctype=ctype0[i], vmin=vmin0[i], vmax=vmax0[i], zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, title=title[i], titlesize=20, change_points=change_points, label_latlon=label_latlon[i])
        if cax[i] is not None:
            # Colourbar
            cbar = plt.colorbar(img, cax=cax[i], extend=extend0[i])
        if u[i] is not None and v[i] is not None:
            # Overlay vectors
            overlay_vectors(ax, u[i], v[i], grid, chunk=chunk, scale=scale)
    plt.suptitle(suptitle, fontsize=22)
    if date_string is not None:
        plt.text(.99, .99, date_string, fontsize=18, ha='right', va='top', transform=fig.transFigure)
    finished_plot(fig, fig_name=fig_name)


# NetCDF interface to latlon_comparison_plot.
# Assumes the two simulations have the same output filename with a single time record.
def read_plot_latlon_comparison (var, expt_name_1, expt_name_2, directory1, directory2, fname, grid=None, zoom_fris=False, xmin=None, xmax=None, ymin=None, ymax=None, vmin=None, vmax=None, vmin_diff=None, vmax_diff=None, extend=None, extend_diff=None, date_string=None, fig_name=None, change_points=None):

    directory1 = real_dir(directory1)
    directory2 = real_dir(directory2)

    # Build the grid if needed
    grid = choose_grid(grid, directory1+fname)

    # Inner function to read and process the variable from the given NetCDF file, and also return the variable title.
    def read_and_process (file_path):
        if var == 'ismr':
            return convert_ismr(mask_except_ice(read_netcdf(file_path, 'SHIfwFlx', time_index=0), grid)), 'Ice shelf melt rate (m/y)'
        elif var == 'bwtemp':
            return select_bottom(mask_3d(read_netcdf(file_path, 'THETA', time_index=0), grid)), 'Bottom water temperature ('+deg_string+'C)'
        elif var == 'bwsalt':
            return select_bottom(mask_3d(read_netcdf(file_path, 'SALT', time_index=0), grid)), 'Bottom water salinity (psu)'
        elif var == 'bwage':
            return select_bottom(mask_3d(read_netcdf(file_path, 'TRAC01', time_index=0), grid)), 'Bottom water age (years)'
        elif var == 'sst':
            return mask_3d(read_netcdf(file_path, 'THETA', time_index=0), grid)[0], 'Sea surface temperature ('+deg_string+'C)'
        elif var == 'sss':
            return mask_3d(read_netcdf(file_path, 'SALT', time_index=0), grid)[0], 'Sea surface salinity (psu)'
        elif var == 'aice':
            return mask_land_ice(read_netcdf(file_path, 'SIarea', time_index=0), grid), 'Sea ice concentration'
        elif var == 'hice':
            return mask_land_ice(read_netcdf(file_path, 'SIheff', time_index=0), grid), 'Sea ice thickness'
        elif var == 'iceprod':
            return mask_land_ice(read_netcdf(file_path, 'SIdHbOCN', time_index=0) + read_netcdf(file_path, 'SIdHbATC', time_index=0) + read_netcdf(file_path, 'SIdHbATO', time_index=0) + read_netcdf(file_path, 'SIdHbFLO', time_index=0), grid)*sec_per_year, 'Net sea ice production (m/y)'
        elif var == 'mld':
            return mask_land_ice(read_netcdf(file_path, 'MXLDEPTH', time_index=0), grid), 'Mixed layer depth (m)'
        elif var == 'vel':
            u = mask_3d(read_netcdf(file_path, 'UVEL', time_index=0), grid, gtype='u')
            v = mask_3d(read_netcdf(file_path, 'VVEL', time_index=0), grid, gtype='v')
            speed, u, v = prepare_vel(u, v, grid, vel_option='avg')
            return speed, u, v, 'Barotropic velocity (m/s)'
        elif var == 'psi':
            return np.sum(mask_3d(read_netcdf(file_path, 'PsiVEL', time_index=0), grid), axis=0)*1e-6, 'Velocity streamfunction (Sv)'
        elif var in ['rho_vavg', 'bwrho']:
            # Assumes MDJWF density
            temp = mask_3d(read_netcdf(file_path, 'THETA', time_index=0), grid)
            salt = mask_3d(read_netcdf(file_path, 'SALT', time_index=0), grid)
            rho_3d = potential_density('MDJWF', salt, temp)-1000
            if var == 'rho_vavg':
                return mask_land(vertical_average(rho_3d, grid), grid), r'Vertically averaged density (kg/m$^3$-1000)'
            elif var == 'bwrho':
                return select_bottom(mask_3d(rho_3d,grid)), r'Bottom density (kg/m$^3$-1000)'

    # Call this for each simulation
    if var == 'vel':
        data_1, u_1, v_1, title = read_and_process(directory1+fname)
        data_2, u_2, v_2 = read_and_process(directory2+fname)[:3]
    else:
        data_1, title = read_and_process(directory1+fname)
        data_2 = read_and_process(directory2+fname)[0]
        u_1 = None
        v_1 = None
        u_2 = None
        v_2 = None
        
    ctype = 'basic'
    if var in ['iceprod', 'psi']:
        ctype = 'plusminus'
    if var in ['ismr', 'vel']:
        ctype = var
    include_shelf = True
    if var in ['sst', 'sss', 'aice', 'hice', 'iceprod', 'mld']:
        include_shelf = False

    # Make the plot
    latlon_comparison_plot(data_1, data_2, grid, include_shelf=include_shelf, ctype=ctype, vmin=vmin, vmax=vmax, vmin_diff=vmin_diff, vmax_diff=vmax_diff, zoom_fris=zoom_fris, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, date_string=date_string, title1=expt_name_1, title2=expt_name_2, suptitle=title, fig_name=fig_name, change_points=change_points, extend=extend, extend_diff=extend_diff, u_1=u_1, v_1=v_1, u_2=u_2, v_2=v_2)
    
    
        
    
    
    

    
