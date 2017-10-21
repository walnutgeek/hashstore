var path = require("path");
var webpack = require("webpack");
var CopyWebpackPlugin = require('copy-webpack-plugin');

const FILE_LOCATION = 'name=[name].[ext]';

function abs_dir(r) { return path.resolve(__dirname, r) ; }

function url_loader(mime) {
    return 'url?limit=10000&' + FILE_LOCATION +
        '&minetype=' + mime ; }

var name = 'hashstore';

function cfg(entry_point, out_file){
  var c = {
    entry: entry_point,
    output: {
        path: abs_dir(name + '/components'),
        filename: out_file,
        publicPath: "/.components/" ,
        library: name },
    devtool: "source-map",
    module: {
      preLoaders: [
        {
          test: /\.js$/,
          loaders: ['jshint'],
          include: ["web"].map(abs_dir)
        }
      ],
      loaders: [
          { test: /\.js$/,
              loader: "uglify" },
          { test: /\.scss$/,
              loader: 'style?minimize!css!sass?sourceMap' },
          { test: /\.css$/,
              loader: 'style?minimize!css' },
          { test: /\.(png|jpg)$/,
              loader: 'file?' + FILE_LOCATION },
          { test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
              loader: "file?" + FILE_LOCATION },
          { test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
              loader: url_loader("application/font-woff") },
          { test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
              loader: url_loader("application/font-woff2") },
          { test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
              loader: url_loader("application/octet-stream") },
          { test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
              loader: url_loader("image/svg+xml") },
          { test: /\.json$/,
              loader: 'json' },
      ],
    },
    plugins: [
      new webpack.IgnorePlugin(/jsdom/),
      new CopyWebpackPlugin([
            { from: 'web/tests.html' },
            { from: 'web/index.html' },
      ])
    ]
  };
  return c;
}

module.exports = [
  cfg("./web/index.js",name + ".js"),
  //cfg("mocha!./web/tests.js","testBundle.js")
];