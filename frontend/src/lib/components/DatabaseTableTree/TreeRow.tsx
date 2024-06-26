import './TreeRow.scss'

import { IconChevronDown } from '@posthog/icons'
import { Spinner } from '@posthog/lemon-ui'
import clsx from 'clsx'
import { IconChevronRight } from 'lib/lemon-ui/icons'
import { useCallback, useState } from 'react'
import { DataWarehouseTableType } from 'scenes/data-warehouse/types'

import { DatabaseTableTree, TreeItemFolder, TreeItemLeaf } from './DatabaseTableTree'

export interface TreeRowProps {
    item: TreeItemLeaf
    depth: number
    onClick?: (row: DataWarehouseTableType) => void
    selected?: boolean
}

export function TreeRow({ item, onClick, selected }: TreeRowProps): JSX.Element {
    const _onClick = useCallback(() => {
        onClick && onClick(item.table)
    }, [])

    return (
        <li>
            <div className={clsx('TreeRow text-ellipsis', selected ? 'TreeRow__selected' : '')} onClick={_onClick}>
                <span className="mr-2">{item.icon}</span>
                <div className="overflow-hidden text-ellipsis whitespace-nowrap">{item.table.name}</div>
            </div>
        </li>
    )
}

export interface TreeFolderRowProps {
    item: TreeItemFolder
    depth: number
    onClick?: (row: DataWarehouseTableType) => void
    selectedRow?: DataWarehouseTableType | null
}

export function TreeFolderRow({ item, depth, onClick, selectedRow }: TreeFolderRowProps): JSX.Element {
    const [collapsed, setCollapsed] = useState(false)
    const { name, items, emptyLabel } = item

    const _onClick = useCallback(() => {
        setCollapsed(!collapsed)
    }, [collapsed])

    return (
        <li>
            <div className={clsx('TreeRow', 'font-bold')} onClick={_onClick}>
                <span className="mr-2">{collapsed ? <IconChevronRight /> : <IconChevronDown />}</span>
                {name}
            </div>
            {!collapsed &&
                (items.length > 0 ? (
                    <DatabaseTableTree
                        items={items}
                        depth={depth + 1}
                        onSelectRow={onClick}
                        selectedRow={selectedRow}
                        style={{ marginLeft: `2rem`, padding: 0 }}
                    />
                ) : (
                    <div
                        // eslint-disable-next-line react/forbid-dom-props
                        style={{
                            marginLeft: `${2 * depth}rem`,
                        }}
                    >
                        {item.isLoading ? (
                            <Spinner className="mt-2" />
                        ) : emptyLabel ? (
                            emptyLabel
                        ) : (
                            <span className="text-muted">No tables found</span>
                        )}
                    </div>
                ))}
        </li>
    )
}
