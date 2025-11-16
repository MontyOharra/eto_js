Can you break down and explain the following VBA code:

'  Copyright © 2018 Thomas F. Crabtree, Jr. All rights reserved

Option Compare Database
Option Explicit
Option Base 1

Function NextOrderNo() As Double

    Dim db As Database
    Set db = CurrentDb
    
    'Dim Orders As Recordset
    'Set Orders = db.OpenRecordset("HTC200_G040_Q216_10_10 All Orders", dbOpenDynaset)
    
    Dim OrdersInWork As Recordset
    Set OrdersInWork = db.OpenRecordset("HTC300_G040_T005 Orders In Work", dbOpenDynaset)
    
    Dim LON As Recordset
    Set LON = db.OpenRecordset("HTC300_G040_T000 Last OrderNo Assigned", dbOpenDynaset)
    
    Dim FAns As Double
    
    'Add 1 to the last order number assigned (LON)
    
'Stop
    
    With LON
        If Not .EOF Then
            .MoveFirst
            Do Until .EOF
                If Forms![HTC200_G000_F000 Main Menu]!CoID = !lon_coid And _
                    Forms![HTC200_G000_F000 Main Menu]!BrID = !lon_brid Then
                        FAns = !lon_orderno + 1
                End If
                Exit Do
            Loop
        Else
            .AddNew
                !lon_coid = Forms![HTC200_G030_F100 Orders Selection]!m_coid
                !lon_brid = Forms![HTC200_G030_F100 Orders Selection]!m_brid
                !lon_orderno = 1
            .Update
        End If
    End With
    
    'With Orders
    '    .MoveFirst
    '    .MoveLast
    '    Fans = !M_OrderNo + 1
    'End With

    'Read through the orders in work.  If the current FANS is found, and 1 to FANS and read through the orders in work again (beginning at the top)
    'if the current FANS isn't in orders in work, then add the current FANS to the OIW table and pass it on as the next order number to assign.
    
    Dim OIWFound As Boolean: OIWFound = True
    Dim ThisOIW As String, TgtOIW As String
      
    TgtOIW = String(3 - Len(Trim(Forms![HTC200_G000_F000 Main Menu]!CoID)), "0") & Trim(Forms![HTC200_G000_F000 Main Menu]!CoID) & "."
    TgtOIW = TgtOIW & String(5 - Len(Trim(Forms![HTC200_G000_F000 Main Menu]!BrID)), "0") & Trim(Forms![HTC200_G000_F000 Main Menu]!BrID) & "."
    TgtOIW = TgtOIW & String(8 - Len(Trim(Str(FAns))), "0") & Trim(Str(FAns))
    
     With OrdersInWork
        Do Until Not OIWFound
            If Not .EOF Then
                .MoveFirst
                Do Until .EOF
                    ThisOIW = String(3 - Len(Trim(Str(!oiw_coid))), "0") & Trim(Str(!oiw_brid)) & "."
                    ThisOIW = ThisOIW & String(5 - Len(Trim(Str(!oiw_brid))), "0") & Trim(Str(!oiw_brid)) & "."
                    ThisOIW = ThisOIW & String(8 - Len(Trim(Str(!oiw_orderno))), "0") & Trim(Str(!oiw_orderno))
                    If ThisOIW = TgtOIW Then
                        OIWFound = True
                        FAns = FAns + 1
                        TgtOIW = String(3 - Len(Trim(Forms![HTC200_G000_F000 Main Menu]!CoID)), "0") & _
                                                        Trim(Forms![HTC200_G000_F000 Main Menu]!CoID) & "."
                        TgtOIW = TgtOIW & String(5 - Len(Trim(Forms![HTC200_G000_F000 Main Menu]!BrID)), "0") & _
                                                        Trim(Forms![HTC200_G000_F000 Main Menu]!BrID) & "."
                        TgtOIW = TgtOIW & String(8 - Len(Trim(Str(FAns))), "0") & _
                                                        Trim(Str(FAns))
                        .MoveFirst
                        'Exit Do
                    End If
                    .MoveNext
                Loop
                If .EOF Then
                    OIWFound = False
                End If
            Else
                OIWFound = False
                'FAns = 1
            End If
        Loop
   
        .AddNew
            !oiw_coid = Forms![HTC200_G000_F000 Main Menu]!CoID
            !oiw_brid = Forms![HTC200_G000_F000 Main Menu]!BrID
            !oiw_orderno = FAns
            !oiw_when = Now()
            !oiw_user = fOSUserName()
        .Update
            
    End With
        
    NextOrderNo = FAns

End Function

