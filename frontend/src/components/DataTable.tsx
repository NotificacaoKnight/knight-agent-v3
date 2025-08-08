import React, { useState, useCallback, useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table"
import { Input } from "./ui/input"
import { Search, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

interface Column<T> {
  accessorKey?: string;
  header: string | ((props: any) => React.ReactNode);
  cell?: (props: { row: { original: T; getValue: (key: string) => any } }) => React.ReactNode;
  id?: string;
}

interface DataTableProps<TData> {
  columns: Column<TData>[]
  data: TData[]
  searchKey?: string
  searchPlaceholder?: string
  actionButton?: React.ReactNode
}

interface SortConfig {
  field: string;
  direction: 'asc' | 'desc';
}

export function DataTable<TData extends Record<string, any>>({
  columns,
  data,
  searchKey,
  searchPlaceholder = "Buscar...",
  actionButton,
}: DataTableProps<TData>) {
  const [searchValue, setSearchValue] = useState("");
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(null);

  // Helper function to sort data - extracted for clarity and reusability
  const sortData = useCallback((dataToSort: TData[], config: SortConfig | null): TData[] => {
    if (!config) return dataToSort;
    
    return [...dataToSort].sort((a, b) => {
      let aVal = a[config.field];
      let bVal = b[config.field];
      
      // Handle different data types consistently
      if (aVal === null || aVal === undefined) aVal = '';
      if (bVal === null || bVal === undefined) bVal = '';
      
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      
      // Handle numeric values
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return config.direction === 'asc' ? aVal - bVal : bVal - aVal;
      }
      
      // Handle dates
      if (aVal instanceof Date && bVal instanceof Date) {
        return config.direction === 'asc' 
          ? aVal.getTime() - bVal.getTime() 
          : bVal.getTime() - aVal.getTime();
      }
      
      // Default string comparison
      if (aVal < bVal) return config.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return config.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, []);

  // Combined data processing with guaranteed sorting execution
  const processedData = useMemo(() => {
    let result = data;
    
    // Apply search filter first
    if (searchValue && searchKey) {
      result = result.filter(item => {
        const value = item[searchKey];
        return String(value).toLowerCase().includes(searchValue.toLowerCase());
      });
    }
    
    // Apply sorting - this will always be applied if sortConfig exists
    result = sortData(result, sortConfig);
    
    return result;
  }, [data, searchValue, searchKey, sortConfig, sortData]);

  const handleSort = useCallback((field: string) => {
    // Use functional update to ensure we get the most recent state
    setSortConfig(current => {
      if (current?.field === field) {
        // If clicking the same field, toggle direction
        return {
          field,
          direction: current.direction === 'asc' ? 'desc' : 'asc'
        };
      } else {
        // If clicking a different field, sort ascending
        return {
          field,
          direction: 'asc'
        };
      }
    });
  }, []);

  return (
    <div className="space-y-6">
      {(searchKey || actionButton) && (
        <div className="flex items-center gap-4">
          <div className="relative max-w-sm">
            {searchKey && (
              <>
                <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder={searchPlaceholder}
                  value={searchValue}
                  onChange={(event) => setSearchValue(event.target.value)}
                  className="pl-8"
                />
              </>
            )}
          </div>
          {actionButton && (
            <div>
              {actionButton}
            </div>
          )}
        </div>
      )}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column, index) => {
                const isSorted = sortConfig?.field === column.accessorKey;
                const sortDirection = isSorted && sortConfig ? sortConfig.direction : null;
                
                return (
                  <TableHead key={column.id || index} className="text-left">
                    {typeof column.header === 'function' ? (
                      column.header({ column: { toggleSorting: () => column.accessorKey && handleSort(column.accessorKey) } })
                    ) : column.accessorKey ? (
                      <div
                        onClick={() => handleSort(column.accessorKey!)}
                        className="flex items-center cursor-pointer font-medium text-left hover:text-foreground transition-colors"
                      >
                        {column.header}
                        {isSorted ? (
                          sortDirection === 'asc' ? (
                            <ArrowUp className="ml-2 h-4 w-4 text-accent" />
                          ) : (
                            <ArrowDown className="ml-2 h-4 w-4 text-accent" />
                          )
                        ) : (
                          <ArrowUpDown className="ml-2 h-4 w-4 opacity-50 hover:opacity-100 transition-opacity" />
                        )}
                      </div>
                    ) : (
                      column.header
                    )}
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {processedData.length ? (
              processedData.map((item, index) => {
                // Create a more stable key using item properties or fallback to index
                const itemKey = item.id || item.title || item.name || index;
                return (
                  <TableRow key={`row-${itemKey}-${index}`}>
                    {columns.map((column, colIndex) => {
                      const columnKey = column.id || column.accessorKey || colIndex;
                      return (
                        <TableCell key={`cell-${columnKey}-${colIndex}`}>
                          {column.cell ? (
                            column.cell({
                              row: {
                                original: item,
                                getValue: (key: string) => item[key]
                              }
                            })
                          ) : column.accessorKey ? (
                            String(item[column.accessorKey])
                          ) : (
                            ''
                          )}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  Nenhum resultado encontrado.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}