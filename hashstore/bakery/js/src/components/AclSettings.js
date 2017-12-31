import React from 'react';
import AltContainer from 'alt-container';
import {ToLink} from './common_components'
import AclStore from '../stores/AclStore';
import AclActions from '../stores/AclActions';



export const AclSettings = ({match}) => {
    const {path} = match.params;
    AclActions.getAcls();
    return (
        <AltContainer store={AclStore}>
            <AclSettingsBody />
        </AltContainer>);
};
export default AclSettings;


class AclSettingsBody extends React.Component {
    render() {
        let {acls} = this.props;
        acls = acls || [];
        return (<div>
            <h1>AclSettings</h1>
            <table className="pt-table pt-bordered">
              <thead>
                <tr>
                  <th>Permission</th>
                  <th>Cake</th>
                </tr>
              </thead>
              <tbody>
              { acls.map( (acl) =>(
                <tr>
                    <td>
                        {acl.permission}
                    </td>
                    <td>
                        { !acl.cake ? "" :
                        <ToLink to={acl.cake.link()}>
                            {acl.cake.short()}
                        </ToLink>}
                    </td>
                </tr>
              ))}
              </tbody>
            </table>
        </div>);
    }
}