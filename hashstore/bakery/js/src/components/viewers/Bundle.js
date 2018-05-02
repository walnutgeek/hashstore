import React from 'react';
import Cake from "../../utils/Cake";
import {ToLink} from "../common_components";

const Bundle = {
    accept_types: ["HSB"],

    render({path, info, content}) {
        if(content && path){
            let hsb = JSON.parse(content);
            const rows = _.map(hsb[0], (name, i) =>
                ({name, nlink: path.child(name),
                    cake: Cake.ensureCake(hsb[1][i])}));
            return (<table className="pt-table pt-bordered">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Cake</th>
                </tr>
              </thead>
              <tbody>
                {_.map(rows, ({name,nlink,cake}) =>(
                    <tr>
                        <td>
                            <ToLink to={"/"+nlink.toString()}>
                                {name}
                            </ToLink>
                        </td>
                        <td>
                            { cake === null ? "" : (
                                <ToLink
                                    to={cake.link(path.aliasPath.cakepath())}>
                                    {cake.displayName()}
                                </ToLink> )
                            }
                        </td>
                    </tr>))}
              </tbody>
            </table>);
        }else{
            return <div />;
        }
    }
};
export default Bundle;
