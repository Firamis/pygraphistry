import copy, numpy, pandas, pyarrow as pa, sys, uuid

from .util import (error, in_ipython, make_iframe, random_string, warn)

from .bolt_util import (
    bolt_graph_to_edges_dataframe,
    bolt_graph_to_nodes_dataframe,
    node_id_key,
    start_node_id_key,
    end_node_id_key,
    to_bolt_driver)

from .arrow_uploader import ArrowUploader
from .nodexlistry import NodeXLGraphistry
from .tigeristry import Tigeristry

maybe_cudf = None
try:
    import cudf
    maybe_cudf = cudf
except ImportError:
    1

class Plotter(object):
    """Graph plotting class.

    Created using ``Graphistry.bind()``.

    Chained calls successively add data and visual encodings, and end with a plot call.

    To streamline reuse and replayable notebooks, Plotter manipulations are immutable. Each chained call returns a new instance that derives from the previous one. The old plotter or the new one can then be used to create different graphs.

    The class supports convenience methods for mixing calls across Pandas, NetworkX, and IGraph.
    """


    _defaultNodeId = '__nodeid__'


    def __init__(self):
        # Bindings
        self._edges = None
        self._nodes = None
        self._source = None
        self._destination = None
        self._node = None
        self._edge_title = None
        self._edge_label = None
        self._edge_color = None
        self._edge_source_color = None
        self._edge_destination_color = None
        self._edge_size = None
        self._edge_weight = None
        self._edge_icon = None
        self._edge_opacity = None
        self._point_title = None
        self._point_label = None
        self._point_color = None
        self._point_size = None
        self._point_weight = None
        self._point_icon = None
        self._point_opacity = None
        self._point_x = None
        self._point_y = None
        # Settings
        self._height = 500
        self._render = True
        self._url_params = {'info': 'true'}
        # Metadata
        self._name = None
        self._description = None
        self._style = None
        self._complex_encodings = {
            'node_encodings': {'current': {}, 'default': {} },
            'edge_encodings': {'current': {}, 'default': {} }
        }
        # Integrations
        self._bolt_driver = None
        self._tigergraph = None


    def __repr__(self):
        bindings = ['edges', 'nodes', 'source', 'destination', 'node', 
                    'edge_label', 'edge_color', 'edge_size', 'edge_weight', 'edge_title', 'edge_icon', 'edge_opacity',
                    'edge_source_color', 'edge_destination_color',
                    'point_label', 'point_color', 'point_size', 'point_weight', 'point_title', 'point_icon', 'point_opacity',
                    'point_x', 'point_y']
        settings = ['height', 'url_params']

        rep = {'bindings': dict([(f, getattr(self, '_' + f)) for f in bindings]),
               'settings': dict([(f, getattr(self, '_' + f)) for f in settings])}
        if in_ipython():
            from IPython.lib.pretty import pretty
            return pretty(rep)
        else:
            return str(rep)

    def addStyle(self, fg=None, bg=None, page=None, logo=None):
        """Set general visual styles
        
        See .bind() and .settings(url_params={}) for additional styling options, and style() for another way to set the same attributes.

        To facilitate reuse and replayable notebooks, the addStyle() call is chainable. Invocation does not effect the old style: it instead returns a new Plotter instance with the new styles added to the existing ones. Both the old and new styles can then be used for different graphs.

        addStyle() will extend the existing style settings, while style() will replace any in the same group

        :param fg: Dictionary {'blendMode': str} of any valid CSS blend mode
        :type fg: dict.

        :param bg: Nested dictionary of page background properties. {'color': str, 'gradient': {'kind': str, 'position': str, 'stops': list }, 'image': { 'url': str, 'width': int, 'height': int, 'blendMode': str }
        :type bg: dict.

        :param logo: Nested dictionary of logo properties. { 'url': str, 'autoInvert': bool, 'position': str, 'dimensions': { 'maxWidth': int, 'maxHeight': int }, 'crop': { 'top': int, 'left': int, 'bottom': int, 'right': int }, 'padding': { 'top': int, 'left': int, 'bottom': int, 'right': int}, 'style': str}        
        :type logo: dict.

        :param page: Dictionary of page metadata settings. { 'favicon': str, 'title': str } 
        :type page: dict.

        :returns: Plotter.
        :rtype: Plotter.

        **Example: Chained merge - results in color, blendMode, and url being set**
            ::
                g2 =  g.addStyle(bg={'color': 'black'}, fg={'blendMode': 'screen'})
                g3 = g2.addStyle(bg={'image': {'url': 'http://site.com/watermark.png'}})
                
        **Example: Overwrite - results in blendMode multiply**
            ::
                g2 =  g.addStyle(fg={'blendMode': 'screen'})
                g3 = g2.addStyle(fg={'blendMode': 'multiply'})

        **Example: Gradient background**
            ::
              g.addStyle(bg={'gradient': {'kind': 'linear', 'position': 45, 'stops': [['rgb(0,0,0)', '0%'], ['rgb(255,255,255)', '100%']]}})
              
        **Example: Page settings**
            ::
              g.addStyle(page={'title': 'Site - {{ name }}', 'favicon': 'http://site.com/logo.ico'})

        """
        style = copy.deepcopy(self._style or {})
        o = {'fg': fg, 'bg': bg, 'page': page, 'logo': logo}
        for k, v in o.items():
            if not (v is None):
                if isinstance(v, dict):
                    if not (k in style) or (style[k] is None):
                        style[k] = {}
                    for k2, v2 in v.items():
                        style[k][k2] = v2
                else:
                    style[k] = v
        res = self.bind()
        res._style = style
        return res
        


    def style(self, fg=None, bg=None, page=None, logo=None):
        """Set general visual styles
        
        See .bind() and .settings(url_params={}) for additional styling options, and addStyle() for another way to set the same attributes.

        To facilitate reuse and replayable notebooks, the style() call is chainable. Invocation does not effect the old style: it instead returns a new Plotter instance with the new styles added to the existing ones. Both the old and new styles can then be used for different graphs.

        style() will fully replace any defined parameter in the existing style settings, while addStyle() will merge over previous values

        :param fg: Dictionary {'blendMode': str} of any valid CSS blend mode
        :type fg: dict.

        :param bg: Nested dictionary of page background properties. {'color': str, 'gradient': {'kind': str, 'position': str, 'stops': list }, 'image': { 'url': str, 'width': int, 'height': int, 'blendMode': str }
        :type bg: dict.

        :param logo: Nested dictionary of logo properties. { 'url': str, 'autoInvert': bool, 'position': str, 'dimensions': { 'maxWidth': int, 'maxHeight': int }, 'crop': { 'top': int, 'left': int, 'bottom': int, 'right': int }, 'padding': { 'top': int, 'left': int, 'bottom': int, 'right': int}, 'style': str}        
        :type logo: dict.

        :param page: Dictionary of page metadata settings. { 'favicon': str, 'title': str } 
        :type page: dict.

        :returns: Plotter.
        :rtype: Plotter.

        **Example: Chained merge - results in url and blendMode being set, while color is dropped**
            ::
                g2 =  g.style(bg={'color': 'black'}, fg={'blendMode': 'screen'})
                g3 = g2.style(bg={'image': {'url': 'http://site.com/watermark.png'}})
                
        **Example: Gradient background**
            ::
              g.style(bg={'gradient': {'kind': 'linear', 'position': 45, 'stops': [['rgb(0,0,0)', '0%'], ['rgb(255,255,255)', '100%']]}})
              
        **Example: Page settings**
            ::
              g.style(page={'title': 'Site - {{ name }}', 'favicon': 'http://site.com/logo.ico'})

        """        
        style = copy.deepcopy(self._style or {})
        o = {'fg': fg, 'bg': bg, 'page': page, 'logo': logo}
        for k, v in o.items():
            if not (v is None):
                style[k] = v
        res = self.bind()
        res._style = style
        return res


    def encode_point_color(self, column,
            palette=None, as_categorical=None, as_continuous=None, categorical_mapping=None, default_mapping=None,
            for_default=True, for_current=False):
        """Set point color with more control than bind()

        :param column: Data column name
        :type column: str.

        :param palette: Optional list of color-like strings. Ex: ["black, "#FF0", "rgb(255,255,255)" ]. Used as a gradient for continuous and round-robin for categorical.
        :type palette: list, optional.

        :param as_categorical: Interpret column values as categorical. Ex: Uses palette via round-robin when more values than palette entries.
        :type as_categorical: bool, optional.

        :param as_continuous: Interpret column values as continuous. Ex: Uses palette for an interpolation gradient when more values than palette entries.
        :type as_continuous: bool, optional.

        :param categorical_mapping: Mapping from column values to color-like strings. Ex: {"car": "red", "truck": #000"}
        :type categorical_mapping: dict, optional.

        :param default_mapping: Augment categorical_mapping with mapping for values not in categorical_mapping. Ex: default_mapping="gray".
        :type default_mapping: str, optional.

        :param for_default: Use encoding for when no user override is set. Default on.
        :type for_default: bool, optional.

        :param for_current: Use encoding as currently active. Clearing the active encoding resets it to default, which may be different. Default on.
        :type for_current: bool, optional.

        :returns: Plotter.
        :rtype: Plotter.

        **Example: Set a palette-valued column for the color, same as bind(point_color='my_column')**
            ::
                g2a = g.encode_point_color('my_int32_palette_column')
                g2b = g.encode_point_color('my_int64_rgb_column')

        **Example: Set a cold-to-hot gradient of along the spectrum blue, yellow, red**
            ::
                g2 = g.encode_point_color('my_numeric_col', palette=["blue", "yellow", "red"], as_continuous=True)

        **Example: Round-robin sample from 5 colors in hex format**
            ::
                g2 = g.encode_point_color('my_distinctly_valued_col', palette=["#000", "#00F", "#0F0", "#0FF", "#FFF"], as_categorical=True)

        **Example: Map specific values to specific colors, including with a default**
            ::
                g2a = g.encode_point_color('brands', categorical_mapping={'toyota': 'red', 'ford': 'blue'})
                g2a = g.encode_point_color('brands', categorical_mapping={'toyota': 'red', 'ford': 'blue'}, default_mapping='gray')

        """
        return self.__encode('point', 'color', 'pointColorEncoding',
            column=column, palette=palette, as_categorical=as_categorical, as_continuous=as_continuous,
            categorical_mapping=categorical_mapping, default_mapping=default_mapping,
            for_default=for_default, for_current=for_current)


    def encode_edge_color(self, column,
            palette=None, as_categorical=None, as_continuous=None, categorical_mapping=None, default_mapping=None,
            for_default=True, for_current=False):
        """Set edge color with more control than bind()

        :param column: Data column name
        :type column: str.

        :param palette: Optional list of color-like strings. Ex: ["black, "#FF0", "rgb(255,255,255)" ]. Used as a gradient for continuous and round-robin for categorical.
        :type palette: list, optional.

        :param as_categorical: Interpret column values as categorical. Ex: Uses palette via round-robin when more values than palette entries.
        :type as_categorical: bool, optional.

        :param as_continuous: Interpret column values as continuous. Ex: Uses palette for an interpolation gradient when more values than palette entries.
        :type as_continuous: bool, optional.

        :param categorical_mapping: Mapping from column values to color-like strings. Ex: {"car": "red", "truck": #000"}
        :type categorical_mapping: dict, optional.

        :param default_mapping: Augment categorical_mapping with mapping for values not in categorical_mapping. Ex: default_mapping="gray".
        :type default_mapping: str, optional.

        :param for_default: Use encoding for when no user override is set. Default on.
        :type for_default: bool, optional.

        :param for_current: Use encoding as currently active. Clearing the active encoding resets it to default, which may be different. Default on.
        :type for_current: bool, optional.

        :returns: Plotter.
        :rtype: Plotter.

        **Example: See encode_point_color**
        """

        return self.__encode('edge', 'color',  'edgeColorEncoding',
            column=column, palette=palette, as_categorical=as_categorical, as_continuous=as_continuous,
            categorical_mapping=categorical_mapping, default_mapping=default_mapping,
            for_default=for_default, for_current=for_current)

    def encode_point_size(self, column,
            categorical_mapping=None, default_mapping=None,
            for_default=True, for_current=False):
        """Set point size with more control than bind()

        :param column: Data column name
        :type column: str.

        :param categorical_mapping: Mapping from column values to numbers. Ex: {"car": 100, "truck": 200}
        :type categorical_mapping: dict, optional.

        :param default_mapping: Augment categorical_mapping with mapping for values not in categorical_mapping. Ex: default_mapping=50.
        :type default_mapping: numeric, optional.

        :param for_default: Use encoding for when no user override is set. Default on.
        :type for_default: bool, optional.

        :param for_current: Use encoding as currently active. Clearing the active encoding resets it to default, which may be different. Default on.
        :type for_current: bool, optional.

        :returns: Plotter.
        :rtype: Plotter.

        **Example: Set a numerically-valued column for the size, same as bind(point_size='my_column')**
            ::
                g2a = g.encode_point_size('my_numeric_column')

        **Example: Map specific values to specific colors, including with a default**
            ::
                g2a = g.encode_point_size('brands', categorical_mapping={'toyota': 100, 'ford': 200})
                g2b = g.encode_point_size('brands', categorical_mapping={'toyota': 100, 'ford': 200}, default_mapping=50)

        """
        return self.__encode('point', 'size',  'pointSizeEncoding', column=column,
            categorical_mapping=categorical_mapping, default_mapping=default_mapping,
            for_default=for_default, for_current=for_current)


    def encode_point_icon(self, column,
            categorical_mapping=None, continuous_binning=None, default_mapping=None,
            comparator=None,
            for_default=True, for_current=False,
            as_text=False, blend_mode=None, style=None, border=None, shape=None):
        """Set node icon with more control than bind().
        Values from Font Awesome 4 such as "laptop": https://fontawesome.com/v4.7.0/icons/ , image URLs (http://...), and data URIs (data:...).
        When as_text=True is enabled, values are instead interpreted as raw strings.

        :param column: Data column name
        :type column: str.

        :param categorical_mapping: Mapping from column values to icon name strings. Ex: {"toyota": 'car', "ford": 'truck'}
        :type categorical_mapping: dict, optional.

        :param default_mapping: Augment categorical_mapping with mapping for values not in categorical_mapping. Ex: default_mapping=50.
        :type default_mapping: numeric, optional.

        :param for_default: Use encoding for when no user override is set. Default on.
        :type for_default: bool, optional.

        :param for_current: Use encoding as currently active. Clearing the active encoding resets it to default, which may be different. Default on.
        :type for_current: bool, optional.

        :param as_text: Values should instead be treated as raw strings, instead of icons and images. (Default False.)
        :type as_text: bool, optional.

        :param blend_mode: CSS blend mode
        :type blend_mode: str, optional.

        :param style: CSS filter properties - opacity, saturation, luminosity, grayscale, and more
        :type style: dict, optional

        :param border: Border properties - 'width', 'color', and 'storke'
        :type border: dict, optional

        :returns: Plotter.
        :rtype: Plotter.

        **Example: Set a string column of icons for the point icons, same as bind(point_icon='my_column')**
            ::
                g2a = g.encode_point_icon('my_icons_column')

        **Example: Map specific values to specific icons, including with a default**
            ::
                g2a = g.encode_point_icon('brands', categorical_mapping={'toyota': 'car', 'ford': 'truck'})
                g2b = g.encode_point_icon('brands', categorical_mapping={'toyota': 'car', 'ford': 'truck'}, default_mapping='question')

        **Example: Map countries to abbreviations**
            ::
                g2b = g.encode_point_icon('country_abbrev', as_text=True)
                g2b = g.encode_point_icon('country', as_text=True, categorical_mapping={'England': 'UK', 'America': 'US'}, default_mapping='')

        **Example: Border**
            ::
                g2b = g.encode_point_icon('country', border={'width': 3, color: 'black', 'stroke': 'dashed'}, 'categorical_mapping={'England': 'UK', 'America': 'US'})

        """

        return self.__encode('point', 'icon',  'pointIconEncoding', column=column,
            categorical_mapping=categorical_mapping, continuous_binning=continuous_binning, default_mapping=default_mapping,
            comparator=comparator,
            for_default=for_default, for_current=for_current,
            as_text=as_text, blend_mode=blend_mode, style=style, border=border, shape=shape)

    def encode_edge_icon(self, column,
            categorical_mapping=None, continuous_binning=None, default_mapping=None,
            comparator=None,
            for_default=True, for_current=False,
            as_text=False, blend_mode=None, style=None, border=None, shape=None):
        """Set edge icon with more control than bind()
        Values from Font Awesome 4 such as "laptop": https://fontawesome.com/v4.7.0/icons/ , image URLs (http://...), and data URIs (data:...).
        When as_text=True is enabled, values are instead interpreted as raw strings.

        :param column: Data column name
        :type column: str.

        :param categorical_mapping: Mapping from column values to icon name strings. Ex: {"toyota": 'car', "ford": 'truck'}
        :type categorical_mapping: dict, optional.

        :param default_mapping: Augment categorical_mapping with mapping for values not in categorical_mapping. Ex: default_mapping=50.
        :type default_mapping: numeric, optional.

        :param for_default: Use encoding for when no user override is set. Default on.
        :type for_default: bool, optional.

        :param for_current: Use encoding as currently active. Clearing the active encoding resets it to default, which may be different. Default on.
        :type for_current: bool, optional.

        :param as_text: Values should instead be treated as raw strings, instead of icons and images. (Default False.)
        :type as_text: bool, optional.

        :returns: Plotter.
        :rtype: Plotter.

        **Example: Set a string column of icons for the edge icons, same as bind(edge_icon='my_column')**
            ::
                g2a = g.encode_edge_icon('my_icons_column')

        **Example: Map specific values to specific icons, including with a default**
            ::
                g2a = g.encode_edge_icon('brands', categorical_mapping={'toyota': 'car', 'ford': 'truck'})
                g2b = g.encode_edge_icon('brands', categorical_mapping={'toyota': 'car', 'ford': 'truck'}, default_mapping='question')

        **Example: Map countries to abbreviations**
            ::
                g2a = g.encode_edge_icon('country_abbrev', as_text=True)
                g2b = g.encode_edge_icon('country', as_text=True, categorical_mapping={'England': 'UK', 'America': 'US'}, default_mapping='')

        **Example: Border**
            ::
                g2b = g.encode_edge_icon('country', border={'width': 3, color: 'black', 'stroke': 'dashed'}, 'categorical_mapping={'England': 'UK', 'America': 'US'})

        """
        return self.__encode('edge', 'icon',   'edgeIconEncoding', column=column,
            categorical_mapping=categorical_mapping, continuous_binning=continuous_binning, default_mapping=default_mapping,
            comparator=comparator,
            for_default=for_default, for_current=for_current,
            as_text=as_text, blend_mode=blend_mode, style=style, border=border, shape=shape)


    def encode_point_badge(self, column, position='TopRight',
            categorical_mapping=None, continuous_binning=None, default_mapping=None, comparator=None,
            color=None, bg=None, fg=None,
            for_current=False, for_default=True,
            as_text=None, blend_mode=None, style=None, border=None, shape=None):

        return self.__encode_badge('point', column, position,
            categorical_mapping=categorical_mapping, continuous_binning=continuous_binning, default_mapping=default_mapping, comparator=comparator,
            color=color, bg=bg, fg=fg,
            for_current=for_current, for_default=for_default,
            as_text=as_text, blend_mode=blend_mode, style=style, border=border, shape=shape)


    def encode_edge_badge(self, column, position='TopRight',
            categorical_mapping=None, continuous_binning=None, default_mapping=None, comparator=None,
            color=None, bg=None, fg=None,
            for_current=False, for_default=True,
            as_text=None, blend_mode=None, style=None, border=None, shape=None):

        return self.__encode_badge('edge', column, position,
            categorical_mapping=categorical_mapping, continuous_binning=continuous_binning, default_mapping=default_mapping, comparator=comparator,
            color=color, bg=bg, fg=fg,
            for_current=for_current, for_default=for_default,
            as_text=as_text, blend_mode=blend_mode, style=style, border=border, shape=shape)

    def __encode_badge(self, graph_type, column, position='TopRight',
            categorical_mapping=None, continuous_binning=None, default_mapping=None, comparator=None,
            color=None, bg=None, fg=None,
            for_current=False, for_default=True,
            as_text=None, blend_mode=None, style=None, border=None, shape=None):

        return self.__encode(graph_type, f'badge{position}', f'{graph_type}Badge{position}Encoding',
            column,
            as_categorical=not (categorical_mapping is None),
            as_continuous=not (continuous_binning is None),
            categorical_mapping=categorical_mapping,
            default_mapping=default_mapping,
            for_current=for_current, for_default=for_default,
            as_text=as_text, blend_mode=blend_mode, style=style, border=border,
            continuous_binning=continuous_binning, ##new
            comparator=comparator, ##new
            color=color, bg=bg, fg=fg, shape=shape)


    def __encode(self, graph_type, feature, feature_binding,
            column,
            palette=None,
            as_categorical=None, as_continuous=None,
            categorical_mapping=None, default_mapping=None,
            for_default=True, for_current=False,
            as_text=None, blend_mode=None, style=None, border=None,
            continuous_binning=None, comparator=None,
            color=None, bg=None, fg=None, dimensions=None, shape=None):

        if for_default is None:
            for_default = True
        if for_current is None:
            for_current = False

        #TODO check set to api=3?

        if not (graph_type in ['point', 'edge']):
            raise ValueError({
                    'message': 'graph_type must be "point" or "edge"',
                    'data': {'graph_type': graph_type } })

        if (categorical_mapping is None) and (palette is None) and (continuous_binning is None) and not feature.startswith('badge'):
            return self.bind(**{f'{graph_type}_{feature}': column})

        transform = None
        if not (categorical_mapping is None):
            if not (isinstance(categorical_mapping, dict)):
                raise ValueError({
                    'message': 'categorical mapping should be a dict mapping column names to values',
                    'data': { 'categorical_mapping': categorical_mapping, 'type': str(type(categorical_mapping)) }})
            transform = {
                'variation': 'categorical',
                'mapping': {
                    'categorical': {
                        'fixed': categorical_mapping,
                        **({} if default_mapping is None else {'other': default_mapping})
                    }
                }
            }
        elif not (palette is None):

            #TODO ensure that it is a color? Unclear behavior for sizes, weights, etc.

            if not (isinstance(palette, list)) or not all([isinstance(x, str) for x in palette]):
                raise ValueError({
                    'message': 'palette should be a list of color-like strings: ["#FFFFFF", "white", ...]',
                    'data': { 'palette': palette, 'type': str(type(palette)) }})

            is_categorical = None
            if not (as_categorical is None):
                is_categorical = as_categorical
            elif not (as_continuous is None):
                is_categorical = not as_continuous
            else:
                raise ValueError({'message': 'Must pass in at least one of as_categorical, as_continuous, or categorical_mapping'})

            transform = {
                'variation': 'categorical' if is_categorical else 'continuous',
                'colors': palette
            }
        elif not (continuous_binning is None):
            if not (isinstance(continuous_binning, list)):
                raise ValueError({
                    'message': 'continous_binning should be a list of [comparable or None, mapped_value]',
                    'data': { 'continuous_binning': continuous_binning, 'type': str(type(continuous_binning)) }})

            if as_categorical:
                raise ValueError({'message': 'as_categorical cannot be True when continuous_binning is provided'})
            if as_continuous == False:
                raise ValueError({'message': 'as_continuous cannot be False when continuous_binning is set'})

            transform = {
                'variation': 'continuous',
                'mapping': {
                    'continuous': {
                        'bins': continuous_binning,
                        **({} if comparator is None else {'comparator': comparator}),
                        **({} if default_mapping is None else {'other': default_mapping})
                    }
                }
            }
        elif feature.startswith('badge'):
            transform = {'variation': 'categorical'}
        else:
            raise ValueError({'message': 'Must pass one of parameters palette or categorical_mapping'})

        encoding = {
            'graphType': graph_type,
            'encodingType': feature,
            'attribute': column,
            **transform,
            **({'bg':        bg} if not         (bg is None) else {}),
            **({'color':     color} if not      (color is None) else {}),
            **({'fg':        fg} if not         (fg is None) else {}),

            **({'asText':    as_text} if not    (as_text is None) else {}),
            **({'blendMode': blend_mode} if not (blend_mode is None) else {}),
            **({'style':     style} if not      (style is None) else {}),
            **({'border':    border} if not     (border is None) else {}),
            **({'shape':     shape} if not      (shape is None) else {})
        }

        complex_encodings = copy.deepcopy(self._complex_encodings)

        #point -> node
        graph_type_2 = 'node' if graph_type == 'point' else graph_type

        #NOTE: parameter feature_binding for cases like Legend
        if for_current:
            complex_encodings[f'{graph_type_2}_encodings']['current'][feature_binding] = encoding
        if for_default:
            complex_encodings[f'{graph_type_2}_encodings']['default'][feature_binding] = encoding

        res = copy.copy(self)
        res._complex_encodings = complex_encodings
        return res


    def bind(self, source=None, destination=None, node=None,
             edge_title=None, edge_label=None, edge_color=None, edge_weight=None, edge_size=None, edge_opacity=None, edge_icon=None,
             edge_source_color=None, edge_destination_color=None,
             point_title=None, point_label=None, point_color=None, point_weight=None, point_size=None, point_opacity=None, point_icon=None,
             point_x=None, point_y=None):
        """Relate data attributes to graph structure and visual representation.

        To facilitate reuse and replayable notebooks, the binding call is chainable. Invocation does not effect the old binding: it instead returns a new Plotter instance with the new bindings added to the existing ones. Both the old and new bindings can then be used for different graphs.


        :param source: Attribute containing an edge's source ID
        :type source: String.

        :param destination: Attribute containing an edge's destination ID
        :type destination: String.

        :param node: Attribute containing a node's ID
        :type node: String.

        :param edge_title: Attribute overriding edge's minimized label text. By default, the edge source and destination is used.
        :type edge_title: HtmlString.

        :param edge_label: Attribute overriding edge's expanded label text. By default, scrollable list of attribute/value mappings.
        :type edge_label: HtmlString.

        :param edge_color: Attribute overriding edge's color. rgba (int64) or int32 palette index, see palette definitions <https://graphistry.github.io/docs/legacy/api/0.9.2/api.html#extendedpalette>`_ for values. Based on Color Brewer.
        :type edge_color: int32 | int64.

        :param edge_source_color: Attribute overriding edge's source color if no edge_color, as an rgba int64 value.
        :type edge_source_color: int64.

        :param edge_destination_color: Attribute overriding edge's destination color if no edge_color, as an rgba int64 value.
        :type edge_destination_color: int64.

        :param edge_weight: Attribute overriding edge weight. Default is 1. Advanced layout controls will relayout edges based on this value.
        :type edge_weight: String.

        :param point_title: Attribute overriding node's minimized label text. By default, the node ID is used.
        :type point_title: HtmlString.

        :param point_label: Attribute overriding node's expanded label text. By default, scrollable list of attribute/value mappings.
        :type point_label: HtmlString.

        :param point_color: Attribute overriding node's color.rgba (int64) or int32 palette index, see palette definitions <https://graphistry.github.io/docs/legacy/api/0.9.2/api.html#extendedpalette>`_ for values. Based on Color Brewer.
        :type point_color: int32 | int64.

        :param point_size: Attribute overriding node's size. By default, uses the node degree. The visualization will normalize point sizes and adjust dynamically using semantic zoom.
        :type point_size: HtmlString.

        :param point_x: Attribute overriding node's initial x position. Combine with ".settings(url_params={'play': 0}))" to create a custom layout
        :type point_x: number.

        :param point_y: Attribute overriding node's initial y position. Combine with ".settings(url_params={'play': 0}))" to create a custom layout
        :type point_y: number.

        :returns: Plotter.
        :rtype: Plotter.

        **Example: Minimal**
            ::

                import graphistry
                g = graphistry.bind()
                g = g.bind(source='src', destination='dst')

        **Example: Node colors**
            ::

                import graphistry
                g = graphistry.bind()
                g = g.bind(source='src', destination='dst',
                           node='id', point_color='color')

        **Example: Chaining**
            ::

                import graphistry
                g = graphistry.bind(source='src', destination='dst', node='id')

                g1 = g.bind(point_color='color1', point_size='size1')

                g.bind(point_color='color1b')

                g2a = g1.bind(point_color='color2a')
                g2b = g1.bind(point_color='color2b', point_size='size2b')

                g3a = g2a.bind(point_size='size3a')
                g3b = g2b.bind(point_size='size3b')

        In the above **Chaining** example, all bindings use src/dst/id. Colors and sizes bind to:
            ::

                g: default/default
                g1: color1/size1
                g2a: color2a/size1
                g2b: color2b/size2b
                g3a: color2a/size3a
                g3b: color2b/size3b


        """
        res = copy.copy(self)
        res._source = source or self._source
        res._destination = destination or self._destination
        res._node = node or self._node

        res._edge_title = edge_title or self._edge_title
        res._edge_label = edge_label or self._edge_label
        res._edge_color = edge_color or self._edge_color
        res._edge_source_color = edge_source_color or self._edge_source_color
        res._edge_destination_color = edge_destination_color or self._edge_destination_color
        res._edge_size = edge_size or self._edge_size
        res._edge_weight = edge_weight or self._edge_weight
        res._edge_icon = edge_icon or self._edge_icon
        res._edge_opacity = edge_opacity or self._edge_opacity

        res._point_title = point_title or self._point_title
        res._point_label = point_label or self._point_label
        res._point_color = point_color or self._point_color
        res._point_size = point_size or self._point_size
        res._point_weight = point_weight or self._point_weight
        res._point_opacity = point_opacity or self._point_opacity
        res._point_icon = point_icon or self._point_icon
        res._point_x = point_x or self._point_x
        res._point_y = point_y or self._point_y
        
        return res


    def nodes(self, nodes, node=None):
        """Specify the set of nodes and associated data.

        Must include any nodes referenced in the edge list.

        :param nodes: Nodes and their attributes.
        :type point_size: Pandas dataframe

        :returns: Plotter.
        :rtype: Plotter.

        **Example**
            ::

                import graphistry

                es = pandas.DataFrame({'src': [0,1,2], 'dst': [1,2,0]})
                g = graphistry
                    .bind(source='src', destination='dst')
                    .edges(es)

                vs = pandas.DataFrame({'v': [0,1,2], 'lbl': ['a', 'b', 'c']})
                g = g.bind(node='v').nodes(vs)

                g.plot()

        **Example**
            ::

                import graphistry

                es = pandas.DataFrame({'src': [0,1,2], 'dst': [1,2,0]})
                g = graphistry.edges(es, 'src', 'dst')

                vs = pandas.DataFrame({'v': [0,1,2], 'lbl': ['a', 'b', 'c']})
                g = g.nodes(vs, 'v)

                g.plot()
        """

        base = self.bind(node=node) if not node is None else self
        res = copy.copy(base)
        res._nodes = nodes
        return res

    def name(self, name):
        """Upload name

        :param name: Upload name
        :type name: str"""

        res = copy.copy(self)
        res._name = name
        return res

    def description(self, description):
        """Upload description

        :param description: Upload description
        :type description: str"""

        res = copy.copy(self)
        res._description = description
        return res


    def edges(self, edges, source=None, destination=None):
        """Specify edge list data and associated edge attribute values.

        :param edges: Edges and their attributes.
        :type point_size: Pandas dataframe, NetworkX graph, or IGraph graph.

        :returns: Plotter.
        :rtype: Plotter.

        **Example**
            ::

                import graphistry
                df = pandas.DataFrame({'src': [0,1,2], 'dst': [1,2,0]})
                graphistry
                    .bind(source='src', destination='dst')
                    .edges(df)
                    .plot()

        **Example**
            ::
                import graphistry
                df = pandas.DataFrame({'src': [0,1,2], 'dst': [1,2,0]})
                graphistry
                    .edges(df, 'src', 'dst')
                    .plot()

        """

        base = self
        if not (source is None):
            base = base.bind(source=source)
        if not (destination is None):
            base = base.bind(destination=destination)

        res = copy.copy(base)
        res._edges = edges
        return res


    def graph(self, ig):
        """Specify the node and edge data.

        :param ig: Graph with node and edge attributes.
        :type ig: NetworkX graph or an IGraph graph.

        :returns: Plotter.
        :rtype: Plotter.
        """

        res = copy.copy(self)
        res._edges = ig
        res._nodes = None
        return res


    def settings(self, height=None, url_params={}, render=None):
        """Specify iframe height and add URL parameter dictionary.

        The library takes care of URI component encoding for the dictionary.

        :param height: Height in pixels.
        :type height: Integer.

        :param url_params: Dictionary of querystring parameters to append to the URL.
        :type url_params: Dictionary

        :param render: Whether to render the visualization using the native notebook environment (default True), or return the visualization URL
        :type render: Boolean

        """

        res = copy.copy(self)
        res._height = height or self._height
        res._url_params = dict(self._url_params, **url_params)
        res._render = self._render if render is None else render
        return res


    def plot(self, graph=None, nodes=None, name=None, description=None, render=None, skip_upload=False):
        """Upload data to the Graphistry server and show as an iframe of it.

        Uses the currently bound schema structure and visual encodings.
        Optional parameters override the current bindings.

        When used in a notebook environment, will also show an iframe of the visualization.

        :param graph: Edge table or graph.
        :type graph: Pandas dataframe, NetworkX graph, or IGraph graph.

        :param nodes: Nodes table.
        :type nodes: Pandas dataframe.

        :param name: Upload name.
        :type name: Optional str.

        :param description: Upload description.
        :type description: Optional str.

        :param render: Whether to render the visualization using the native notebook environment (default True), or return the visualization URL
        :type render: Boolean

        :param skip_upload: Return node/edge/bindings that would have been uploaded. By default, upload happens.
        :type skip_upload: Boolean. 

        **Example: Simple**
            ::

                import graphistry
                es = pandas.DataFrame({'src': [0,1,2], 'dst': [1,2,0]})
                graphistry
                    .bind(source='src', destination='dst')
                    .edges(es)
                    .plot()

        **Example: Shorthand**
            ::

                import graphistry
                es = pandas.DataFrame({'src': [0,1,2], 'dst': [1,2,0]})
                graphistry
                    .bind(source='src', destination='dst')
                    .plot(es)

        """

        if graph is None:
            if self._edges is None:
                error('Graph/edges must be specified.')
            g = self._edges
        else:
            g = graph
        n = self._nodes if nodes is None else nodes
        name = name or self._name or ("Untitled " + random_string(10))
        description = description or self._description or ("")

        self._check_mandatory_bindings(not isinstance(n, type(None)))

        from .pygraphistry import PyGraphistry
        api_version = PyGraphistry.api_version()
        if api_version == 1:
            dataset = self._plot_dispatch(g, n, name, description, 'json', self._style)
            if skip_upload:
                return dataset
            info = PyGraphistry._etl1(dataset)
        elif api_version == 2:
            dataset = self._plot_dispatch(g, n, name, description, 'vgraph', self._style)
            if skip_upload:
                return dataset
            info = PyGraphistry._etl2(dataset)
        elif api_version == 3:
            PyGraphistry.refresh()
            dataset = self._plot_dispatch(g, n, name, description, 'arrow', self._style)
            if skip_upload:
                return dataset
            #fresh
            dataset.token = PyGraphistry.api_token()
            dataset.post()
            info = {
                'name': dataset.dataset_id,
                'type': 'arrow',
                'viztoken': str(uuid.uuid4())
            }

        viz_url = PyGraphistry._viz_url(info, self._url_params)
        cfg_client_protocol_hostname = PyGraphistry._config['client_protocol_hostname']
        full_url = ('%s:%s' % (PyGraphistry._config['protocol'], viz_url)) if cfg_client_protocol_hostname is None else viz_url

        if (render == False) or ((render is None) and not self._render):
            return full_url
        elif (render == True) or in_ipython():
            from IPython.core.display import HTML
            return HTML(make_iframe(full_url, self._height))
        else:
            import webbrowser
            webbrowser.open(full_url)
            return full_url


    def pandas2igraph(self, edges, directed=True):
        """Convert a pandas edge dataframe to an IGraph graph.

        Uses current bindings. Defaults to treating edges as directed.

        **Example**
            ::

                import graphistry
                g = graphistry.bind()

                es = pandas.DataFrame({'src': [0,1,2], 'dst': [1,2,0]})
                g = g.bind(source='src', destination='dst')

                ig = g.pandas2igraph(es)
                ig.vs['community'] = ig.community_infomap().membership
                g.bind(point_color='community').plot(ig)
        """


        import igraph
        self._check_mandatory_bindings(False)
        self._check_bound_attribs(edges, ['source', 'destination'], 'Edge')
        
        self._node = self._node or Plotter._defaultNodeId
        eattribs = edges.columns.values.tolist()
        eattribs.remove(self._source)
        eattribs.remove(self._destination)
        cols = [self._source, self._destination] + eattribs
        etuples = [tuple(x) for x in edges[cols].values]
        return igraph.Graph.TupleList(etuples, directed=directed, edge_attrs=eattribs,
                                      vertex_name_attr=self._node)


    def igraph2pandas(self, ig):
        """Under current bindings, transform an IGraph into a pandas edges dataframe and a nodes dataframe.

        **Example**
            ::

                import graphistry
                g = graphistry.bind()

                es = pandas.DataFrame({'src': [0,1,2], 'dst': [1,2,0]})
                g = g.bind(source='src', destination='dst').edges(es)

                ig = g.pandas2igraph(es)
                ig.vs['community'] = ig.community_infomap().membership

                (es2, vs2) = g.igraph2pandas(ig)
                g.nodes(vs2).bind(point_color='community').plot()
        """

        def get_edgelist(ig):
            idmap = dict(enumerate(ig.vs[self._node]))
            for e in ig.es:
                t = e.tuple
                yield dict({self._source: idmap[t[0]], self._destination: idmap[t[1]]},
                            **e.attributes())

        self._check_mandatory_bindings(False)
        if self._node is None:
            ig.vs[Plotter._defaultNodeId] = [v.index for v in ig.vs]
            self._node = Plotter._defaultNodeId
        elif self._node not in ig.vs.attributes():
            error('Vertex attribute "%s" bound to "node" does not exist.' % self._node)

        edata = get_edgelist(ig)
        ndata = [v.attributes() for v in ig.vs]
        nodes = pandas.DataFrame(ndata, columns=ig.vs.attributes())
        cols = [self._source, self._destination] + ig.es.attributes()
        edges = pandas.DataFrame(edata, columns=cols)
        return (edges, nodes)


    def networkx_checkoverlap(self, g):

        import networkx as nx
        [x, y] = [int(x) for x in nx.__version__.split('.')]

        vattribs = None
        if x == 1:
            vattribs = g.nodes(data=True)[0][1] if g.number_of_nodes() > 0 else []
        else:
            vattribs = g.nodes(data=True) if g.number_of_nodes() > 0 else []
        if not (self._node is None) and self._node in vattribs:
            error('Vertex attribute "%s" already exists.' % self._node)

    def networkx2pandas(self, g):

        def get_nodelist(g):
            for n in g.nodes(data=True):
                yield dict({self._node: n[0]}, **n[1])
        def get_edgelist(g):
            for e in g.edges(data=True):
                yield dict({self._source: e[0], self._destination: e[1]}, **e[2])

        self._check_mandatory_bindings(False)
        self.networkx_checkoverlap(g)
        
        self._node = self._node or Plotter._defaultNodeId
        nodes = pandas.DataFrame(get_nodelist(g))
        edges = pandas.DataFrame(get_edgelist(g))
        return (edges, nodes)


    def _check_mandatory_bindings(self, node_required):
        if self._source is None or self._destination is None:
            error('Both "source" and "destination" must be bound before plotting.')
        if node_required and self._node is None:
            error('Node identifier must be bound when using node dataframe.')


    def _check_bound_attribs(self, df, attribs, typ):
        cols = df.columns.values.tolist()
        for a in attribs:
            b = getattr(self, '_' + a)
            if b not in cols:
                error('%s attribute "%s" bound to "%s" does not exist.' % (typ, a, b))


    def _plot_dispatch(self, graph, nodes, name, description, mode='json', metadata=None):

        if isinstance(graph, pandas.core.frame.DataFrame) \
            or isinstance(graph, pa.Table) \
            or ( not (maybe_cudf is None) and isinstance(graph, maybe_cudf.DataFrame) ):
            return self._make_dataset(graph, nodes, name, description, mode, metadata)

        try:
            import igraph
            if isinstance(graph, igraph.Graph):
                (e, n) = self.igraph2pandas(graph)
                return self._make_dataset(e, n, name, description, mode, metadata)
        except ImportError:
            pass

        try:
            import networkx
            if isinstance(graph, networkx.classes.graph.Graph) or \
               isinstance(graph, networkx.classes.digraph.DiGraph) or \
               isinstance(graph, networkx.classes.multigraph.MultiGraph) or \
               isinstance(graph, networkx.classes.multidigraph.MultiDiGraph):
                (e, n) = self.networkx2pandas(graph)
                return self._make_dataset(e, n, name, description, mode, metadata)
        except ImportError:
            pass

        error('Expected Pandas/Arrow/cuDF dataframe(s) or Igraph/NetworkX graph.')


    # Sanitize node/edge dataframe by
    # - dropping indices
    # - dropping edges with NAs in source or destination
    # - dropping nodes with NAs in nodeid
    # - creating a default node table if none was provided.
    # - inferring numeric types of all columns containing numpy objects
    def _sanitize_dataset(self, edges, nodes, nodeid):
        self._check_bound_attribs(edges, ['source', 'destination'], 'Edge')
        elist = edges.reset_index(drop=True) \
                     .dropna(subset=[self._source, self._destination])

        obj_df = elist.select_dtypes(include=[numpy.object_])
        elist[obj_df.columns] = obj_df.apply(pandas.to_numeric, errors='ignore')

        if nodes is None:
            nodes = pandas.DataFrame()
            nodes[nodeid] = pandas.concat([edges[self._source], edges[self._destination]],
                                           ignore_index=True).drop_duplicates()
        else:
            self._check_bound_attribs(nodes, ['node'], 'Vertex')

        nlist = nodes.reset_index(drop=True) \
                     .dropna(subset=[nodeid]) \
                     .drop_duplicates(subset=[nodeid])

        obj_df = nlist.select_dtypes(include=[numpy.object_])
        nlist[obj_df.columns] = obj_df.apply(pandas.to_numeric, errors='ignore')

        return (elist, nlist)


    def _check_dataset_size(self, elist, nlist):
        edge_count = len(elist.index)
        node_count = len(nlist.index)
        graph_size = edge_count + node_count
        if edge_count > 8e6:
            error('Maximum number of edges (8M) exceeded: %d.' % edge_count)
        if node_count > 8e6:
            error('Maximum number of nodes (8M) exceeded: %d.' % node_count)
        if graph_size > 1e6:
            warn('Large graph: |nodes| + |edges| = %d. Layout/rendering might be slow.' % graph_size)


    # Bind attributes for ETL1 by creating a copy of the designated column renamed
    # with magic names understood by ETL1 (eg. pointColor, etc)
    def _bind_attributes_v1(self, edges, nodes):
        def bind(df, pbname, attrib, default=None):
            bound = getattr(self, attrib)
            if bound:
                if bound in df.columns.tolist():
                    df[pbname] = df[bound]
                else:
                    warn('Attribute "%s" bound to %s does not exist.' % (bound, attrib))
            elif default:
                df[pbname] = df[default]

        nodeid = self._node or Plotter._defaultNodeId
        (elist, nlist) = self._sanitize_dataset(edges, nodes, nodeid)
        self._check_dataset_size(elist, nlist)

        bind(elist, 'edgeColor', '_edge_color')
        bind(elist, 'edgeSourceColor', '_edge_source_color')
        bind(elist, 'edgeDestinationColor', '_edge_destination_color')
        bind(elist, 'edgeLabel', '_edge_label')
        bind(elist, 'edgeTitle', '_edge_title')
        bind(elist, 'edgeSize', '_edge_size')
        bind(elist, 'edgeWeight', '_edge_weight')
        bind(elist, 'edgeOpacity', '_edge_opacity')
        bind(elist, 'edgeIcon', '_edge_icon')
        bind(nlist, 'pointColor', '_point_color')
        bind(nlist, 'pointLabel', '_point_label')
        bind(nlist, 'pointTitle', '_point_title', nodeid)
        bind(nlist, 'pointSize', '_point_size')
        bind(nlist, 'pointWeight', '_point_weight')
        bind(nlist, 'pointOpacity', '_point_opacity')
        bind(nlist, 'pointIcon', '_point_icon')
        bind(nlist, 'pointX', '_point_x')
        bind(nlist, 'pointY', '_point_y')
        return (elist, nlist)

    # Bind attributes for ETL2 by an encodings map storing the visual semantic of
    # each bound column.
    def _bind_attributes_v2(self, edges, nodes):
        def bind(enc, df, pbname, attrib, default=None):
            bound = getattr(self, attrib)
            if bound:
                if bound in df.columns.tolist():
                    enc[pbname] = {'attributes' : [bound]}
                else:
                    warn('Attribute "%s" bound to %s does not exist.' % (bound, attrib))
            elif default:
                enc[pbname] = {'attributes': [default]}

        nodeid = self._node or Plotter._defaultNodeId
        (elist, nlist) = self._sanitize_dataset(edges, nodes, nodeid)
        self._check_dataset_size(elist, nlist)

        edge_encodings = {
            'source': {'attributes' : [self._source]},
            'destination': {'attributes': [self._destination]},
        }
        node_encodings = {
            'nodeId': {'attributes': [nodeid]}
        }
        bind(edge_encodings, elist, 'edgeColor', '_edge_color')
        bind(edge_encodings, elist, 'edgeSourceColor', '_edge_source_color')
        bind(edge_encodings, elist, 'edgeDestinationColor', '_edge_destination_color')
        bind(edge_encodings, elist, 'edgeLabel', '_edge_label')
        bind(edge_encodings, elist, 'edgeTitle', '_edge_title')
        bind(edge_encodings, elist, 'edgeSize', '_edge_size')
        bind(edge_encodings, elist, 'edgeWeight', '_edge_weight')
        bind(edge_encodings, elist, 'edgeOpacity', '_edge_opacity')
        bind(edge_encodings, elist, 'edgeIcon', '_edge_icon')
        bind(node_encodings, nlist, 'pointColor', '_point_color')
        bind(node_encodings, nlist, 'pointLabel', '_point_label')
        bind(node_encodings, nlist, 'pointTitle', '_point_title', nodeid)
        bind(node_encodings, nlist, 'pointSize', '_point_size')
        bind(node_encodings, nlist, 'pointWeight', '_point_weight')
        bind(node_encodings, nlist, 'pointOpacity', '_point_opacity')
        bind(node_encodings, nlist, 'pointIcon', '_point_icon')
        bind(node_encodings, nlist, 'pointX', '_point_x')
        bind(node_encodings, nlist, 'pointY', '_point_y')

        encodings = {
            'nodes': node_encodings,
            'edges': edge_encodings
        }
        return (elist, nlist, encodings)

    def _table_to_pandas(self, table) -> pandas.DataFrame:

        if table is None:
            return table

        if isinstance(table, pandas.DataFrame):
            return table

        if isinstance(table, pa.Table):
            return table.to_pandas()
        
        if not (maybe_cudf is None) and isinstance(table, maybe_cudf.DataFrame):
            return table.to_pandas()
        
        raise Exception('Unknown type %s: Could not convert data to Pandas dataframe' % str(type(table)))

    def _table_to_arrow(self, table) -> pa.Table:

        if table is None:
            return table

        if isinstance(table, pa.Table):
            return table
        
        if isinstance(table, pandas.DataFrame):
            return pa.Table.from_pandas(table, preserve_index=False).replace_schema_metadata({})

        if not (maybe_cudf is None) and isinstance(table, maybe_cudf.DataFrame):
            return table.to_arrow()
        
        raise Exception('Unknown type %s: Could not convert data to Arrow' % str(type(table)))


    def _make_dataset(self, edges, nodes, name, description, mode, metadata=None):
        try:
            if len(edges) == 0:
                warn('Graph has no edges, may have rendering issues')
        except:
            1

        #compatibility checks
        if (mode =='json') or (mode == 'vgraph'):
            if not (metadata is None):
                if ('bg' in metadata) or ('fg' in metadata) or ('logo' in metadata) or ('page' in metadata):
                    raise ValueError('Cannot set bg/fg/logo/page in api=1, api=2; try using api=3')
            if not (self._complex_encodings is None \
                or self._complex_encodings == {
                    'node_encodings': {'current': {}, 'default': {} },
                    'edge_encodings': {'current': {}, 'default': {} }
                }):
                    raise ValueError('Cannot set complex encodings ".encode_[point/edge]_[feature]()" in api=1, api=2; try using api=3 or .bind()')

        if mode == 'json':
            edges_df = self._table_to_pandas(edges)
            nodes_df = self._table_to_pandas(nodes)
            return self._make_json_dataset(edges_df, nodes_df, name)
        elif mode == 'vgraph':
            edges_df = self._table_to_pandas(edges)
            nodes_df = self._table_to_pandas(nodes)
            return self._make_vgraph_dataset(edges_df, nodes_df, name)
        elif mode == 'arrow':
            edges_arr = self._table_to_arrow(edges)
            nodes_arr = self._table_to_arrow(nodes)
            return self._make_arrow_dataset(edges=edges_arr, nodes=nodes_arr, name=name, description=description, metadata=metadata)
            #token=None, dataset_id=None, url_params = None)
        else:
            raise ValueError('Unknown mode: ' + mode)


    # Main helper for creating ETL1 payload
    def _make_json_dataset(self, edges, nodes, name):

        from .pygraphistry import PyGraphistry

        (elist, nlist) = self._bind_attributes_v1(edges, nodes)
        edict = elist.where((pandas.notnull(elist)), None).to_dict(orient='records')

        bindings = {'idField': self._node or Plotter._defaultNodeId,
                    'destinationField': self._destination, 'sourceField': self._source}
        dataset = {'name': PyGraphistry._config['dataset_prefix'] + name,
                   'bindings': bindings, 'type': 'edgelist', 'graph': edict}

        if nlist is not None:
            ndict = nlist.where((pandas.notnull(nlist)), None).to_dict(orient='records')
            dataset['labels'] = ndict
        return dataset


    # Main helper for creating ETL2 payload
    def _make_vgraph_dataset(self, edges, nodes, name):
        from . import vgraph

        (elist, nlist, encodings) = self._bind_attributes_v2(edges, nodes)
        nodeid = self._node or Plotter._defaultNodeId

        sources = elist[self._source]
        dests = elist[self._destination]
        elist.drop([self._source, self._destination], axis=1, inplace=True)

        # Filter out nodes which have no edges
        lnodes = pandas.concat([sources, dests], ignore_index=True).unique()
        lnodes_df = pandas.DataFrame(lnodes, columns=[nodeid])
        filtered_nlist = pandas.merge(lnodes_df, nlist, on=nodeid, how='left')

        # Create a map from nodeId to a continuous range of integer [0, #nodes-1].
        # The vgraph protobuf format uses the continous integer ranger as internal nodeIds.
        node_map = dict([(v, i) for i, v in enumerate(lnodes.tolist())])

        dataset = vgraph.create(elist, filtered_nlist, sources, dests, nodeid, node_map, name)
        dataset['encodings'] = encodings
        return dataset

    def _make_arrow_dataset(self, edges: pa.Table, nodes: pa.Table, name: str, description: str, metadata) -> ArrowUploader:

        from .pygraphistry import PyGraphistry

        au = ArrowUploader(
            server_base_path=PyGraphistry.protocol() + '://' + PyGraphistry.server(),
            edges=edges, nodes=nodes,
            name=name, description=description,
            metadata={
                'usertag': PyGraphistry._tag,
                'key': PyGraphistry.api_key(),
                'agent': 'pygraphistry',
                'apiversion' : '3',
                'agentversion': sys.modules['graphistry'].__version__,
                **(metadata or {})
            },
            certificate_validation=PyGraphistry.certificate_validation())
        au.edge_encodings = au.g_to_edge_encodings(self)
        au.node_encodings = au.g_to_node_encodings(self)
        return au

    def bolt(self, driver):
        res = copy.copy(self)
        res._bolt_driver = to_bolt_driver(driver)
        return res


    def cypher(self, query, params={}):

        from .pygraphistry import PyGraphistry

        res = copy.copy(self)
        driver = self._bolt_driver or PyGraphistry._config['bolt_driver']
        with driver.session() as session:
            bolt_statement = session.run(query, **params)
            graph = bolt_statement.graph()
            edges = bolt_graph_to_edges_dataframe(graph)
            nodes = bolt_graph_to_nodes_dataframe(graph)
        return res\
            .bind(\
                node=node_id_key,\
                source=start_node_id_key,\
                destination=end_node_id_key
            )\
            .nodes(nodes)\
            .edges(edges)

    def nodexl(self, xls_or_url, source='default', engine=None, verbose=False):
        
        if not (engine is None):
            print('WARNING: Engine currently ignored, please contact if critical')
        
        return NodeXLGraphistry(self, engine).xls(xls_or_url, source, verbose)


    def tigergraph(self,
        protocol = 'http',
        server = 'localhost',
        web_port = 14240,
        api_port = 9000,
        db = None,
        user = 'tigergraph',
        pwd = 'tigergraph',
        verbose = False
    ):
        """Register Tigergraph connection setting defaults
    
        :param protocol: Protocol used to contact the database.
        :type protocol: Optional string.
        :param server: Domain of the database
        :type server: Optional string.
        :param web_port: 
        :type web_port: Optional integer.
        :param api_port: 
        :type api_port: Optional integer.
        :param db: Name of the database
        :type db: Optional string.    
        :param user:
        :type user: Optional string.    
        :param pwd: 
        :type pwd: Optional string.
        :param verbose: Whether to print operations
        :type verbose: Optional bool.         
        :returns: Plotter.
        :rtype: Plotter.


        **Example: Standard**
                ::

                    import graphistry
                    tg = graphistry.tigergraph(protocol='https', server='acme.com', db='my_db', user='alice', pwd='tigergraph2')                    

        """
        res = copy.copy(self)
        res._tigergraph = Tigeristry(self, protocol, server, web_port, api_port, db, user, pwd, verbose)
        return res


    def gsql_endpoint(self, method_name, args = {}, bindings = {}, db = None, dry_run = False):
        """Invoke Tigergraph stored procedure at a user-definend endpoint and return transformed Plottable
    
        :param method_name: Stored procedure name
        :type method_name: String.
        :param args: Named endpoint arguments
        :type args: Optional dictionary.
        :param bindings: Mapping defining names of returned 'edges' and/or 'nodes', defaults to @@nodeList and @@edgeList
        :type bindings: Optional dictionary.
        :param db: Name of the database, defaults to value set in .tigergraph(...)
        :type db: Optional string.
        :param dry_run: Return target URL without running
        :type dry_run: Bool, defaults to False
        :returns: Plotter.
        :rtype: Plotter.

        **Example: Minimal**
                ::

                    import graphistry
                    tg = graphistry.tigergraph(db='my_db')
                    tg.gsql_endpoint('neighbors').plot()

        **Example: Full**
                ::

                    import graphistry
                    tg = graphistry.tigergraph()
                    tg.gsql_endpoint('neighbors', {'k': 2}, {'edges': 'my_edge_list'}, 'my_db').plot()

        **Example: Read data**
                ::

                    import graphistry
                    tg = graphistry.tigergraph()
                    out = tg.gsql_endpoint('neighbors')
                    (nodes_df, edges_df) = (out._nodes, out._edges)

        """
        return self._tigergraph.gsql_endpoint(self, method_name, args, bindings, db, dry_run)

    def gsql(self, query, bindings = {}, dry_run = False):
        """Run Tigergraph query in interpreted mode and return transformed Plottable
    
        :param query: Code to run
        :type query: String.
        :param bindings: Mapping defining names of returned 'edges' and/or 'nodes', defaults to @@nodeList and @@edgeList
        :type bindings: Optional dictionary.
        :param dry_run: Return target URL without running
        :type dry_run: Bool, defaults to False        
        :returns: Plotter.
        :rtype: Plotter.

        **Example: Minimal**
                ::

                    import graphistry
                    tg = graphistry.tigergraph()
                    tg.gsql(\"\"\"
                    INTERPRET QUERY () FOR GRAPH Storage { 
                        
                        OrAccum<BOOL> @@stop;
                        ListAccum<EDGE> @@edgeList;
                        SetAccum<vertex> @@set;
                        
                        @@set += to_vertex("61921", "Pool");

                        Start = @@set;

                        while Start.size() > 0 and @@stop == false do

                        Start = select t from Start:s-(:e)-:t
                        where e.goUpper == TRUE
                        accum @@edgeList += e
                        having t.type != "Service";
                        end;

                        print @@edgeList;
                    }
                    \"\"\").plot()

       **Example: Full**
                ::

                    import graphistry
                    tg = graphistry.tigergraph()
                    tg.gsql(\"\"\"
                    INTERPRET QUERY () FOR GRAPH Storage { 
                        
                        OrAccum<BOOL> @@stop;
                        ListAccum<EDGE> @@edgeList;
                        SetAccum<vertex> @@set;
                        
                        @@set += to_vertex("61921", "Pool");

                        Start = @@set;

                        while Start.size() > 0 and @@stop == false do

                        Start = select t from Start:s-(:e)-:t
                        where e.goUpper == TRUE
                        accum @@edgeList += e
                        having t.type != "Service";
                        end;

                        print @@my_edge_list;
                    }
                    \"\"\", {'edges': 'my_edge_list'}).plot()
        """        
        return self._tigergraph.gsql(self, query, bindings, dry_run)







