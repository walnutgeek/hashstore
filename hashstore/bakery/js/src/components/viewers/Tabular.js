import React from 'react';
import DataFrame from 'wdf/DataFrame';

const parsers = {
    WDF: DataFrame.parse_wdf,
    CSV: DataFrame.parse_csv,
}
const Tabular = {
    accept_types: ["WDF", "CSV"],

    render({path, info, content}) {
        if(content && path){
            const df =  parsers[info.file_type](content);
            const col_idxs = _.range(df.getColumnCount());
            return (<table className="pt-table pt-bordered">
              <thead>
                <tr>
                {df.getColumnNames().map(n=>(
                  <th>{n}</th>
                ))}
                </tr>
              </thead>
              <tbody>
                {_.range(df.getRowCount()).map((row_idx) =>(
                    <tr>
                    {col_idxs.map((col_idx) =>(
                        <td>
                            {df.get(row_idx,col_idx,'as_string')}
                        </td>
                    ))}
                    </tr>
                ))}
              </tbody>
            </table>);
        }else{
            return <div />;
        }
    }
};
export default Tabular;
