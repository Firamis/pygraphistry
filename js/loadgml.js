/*

    Data generated via facebook/networkx $ python fb.py (manually setting dataset sizes)

*/


"use strict";


var PATH = 'data/gml/';

var $ = require('jQuery'),
    Q = require('Q'),
    _ = require('underscore');

var debug = require("debug")("N-body:load:gml");


function ls () {
    return [
        'output_v100_e207.json',
        'output_v1000_e9803.json',
        'output_v10000_e57292.json',
        'output_v50000_e136204.json',
        'output_v265214_e420045.json'
    ].map(function (v) {
        return PATH + v;
    });
}

/*
    input: path to GML JSON file
        gen from networkx: json.dumps((json_graph.node_link_data(nxg)), indent=1)
    pathstring ->
        {
            nodes: {colors: uint32array, sizes: flaot32array},
            edges: uint32array,
            min: int, max: int, numNodes: int, numEdges: int
        }
*/
function loadGMLJSON (path) {

    var file = typeof window == 'undefined' ?
        Q.denodeify(require('fs').readFile)(path, {encoding: 'utf8'})
    :   Q($.ajax(path, {dataType: "text"}));

    var json = file.then(JSON.parse);

    return json.then(
        function (data) {

            var nodes = data.nodes.slice(0);
            var res = {
                nodes: {
                    colors: new Uint32Array(_.pluck(nodes, 'color')),
                    sizes: new Float32Array(_.pluck(nodes, 'size'))
                },
                edges: data.links.map(function (o) { return [o.source, o.target]; }),
                //BUG some reason
                edgesFlat:
                    new Uint32Array(
                        _.flatten(
                            data.links.map(function (o) {
                                return [o.source, o.target]; }))),
                min: 0,
                max: data.nodes.length,
                numNodes: data.nodes.length,
                numEdges: data.links.length
            };
            return res;
        },
        function (err) {
            console.error('parse error', err);
        });
}

function demo () {

    var out = loadGMLJSON('/Users/lmeyerov/Desktop/Graphistry/experiments/facebook/networkx/output_v1000_e9803.json')
    .then(
        function (v) { console.log('done', v) },
        function (err) { console.log('oops', err, err.stack) });

}

module.exports = {
    ls: ls,
    loadGMLJSON: loadGMLJSON
}