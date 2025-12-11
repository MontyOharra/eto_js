'  Copyright © 2018 Thomas F. Crabtree, Jr. All rights reserved

Option Compare Database
Option Explicit
Option Base 1

Private Sub btn_Add_Click()
' ----------------------------------------------------------------
' Copyright © 2018-2023 Thomas F. Crabtree, Jr. All rights reserved
' Procedure Name: btn_Add_Click
' Purpose: Add New Pick Up and/or Delivery Address
' Procedure Kind: Sub
' Procedure Access: Private
' Author: Tom Crabtree
' Date: 03/29/2023
' Change Log
'       3/29/2023 - set FavLatitude and FavLongitude to empty string on creation
' ----------------------------------------------------------------

    Dim db As Database
    Set db = CurrentDb
    
    Dim Addresses As Recordset
    'Set Addresses = db.OpenRecordset("HTC200_G060_Q010_00 Pkup_Dlvr Addresses", dbOpenDynaset)
    Set Addresses = db.OpenRecordset("HTC300_G060_T010 Addresses", dbOpenDynaset)
    
    Dim Cities As Recordset
    Set Cities = db.OpenRecordset("HTC200_G060_Q012 All ACI in City Zip Seq", dbOpenDynaset)
    
    Dim States As Recordset
    Set States = db.OpenRecordset("HTC010_G000_T000 All State Abbrev", dbOpenDynaset)
    
    Dim ThisCoBr As Recordset
    Set ThisCoBr = db.OpenRecordset("HTC200_G000_T000 ThisCoBr", dbOpenTable)
    ThisCoBr.MoveFirst
    
    Dim Msg, ChkMsg, MsgTitle As String
    Dim Ans As Integer
    
    Dim wrkFavKeyCheck As String
    Dim wrkFavKeyCounts As String
    Dim wrkFavKeyChar(36) As String
    Dim wrkFavKeyCount(36) As Integer
    Dim x, y, EndY, MaxY As Integer
    Dim wrkCharFound As Boolean
    Dim srtWrkFavChar As String
    Dim srtWrkFavCount As Integer
    
    ' when adding a new company, the aci data isn't being set up, so....
    
    'If HTC200_FormIsLoaded("HTC200_G001_F020 New Company") Then
    '    Dim ACIData As Recordset
    '    Set ACIData = db.OpenRecordset("HTC300_G010_T010 DFW_ACI_Data", dbOpenDynaset)
    '
    '    Dim WhatCB As Recordset
    '    Set WhatCB = db.OpenRecordset("HTC200_G000_T000 ThisCoBr", dbOpenTable)
    '
    '    If WhatCB.RecordCount <> 1 Then
    '        MsgTitle = "HTC200_G060_F040 New Address"
    '        Msg = "No ThisCoBr record found"
    '        Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
    '        Exit Sub
    '    Else
    '        WhatCB.MoveFirst
    '        With ACIData
    '            If Not .EOF Then
    '                .MoveFirst
    '                Do Until .EOF
    '                    If !ACICoID = WhatCB!ThisCo And _
    '                        !ACIBrID = WhatCB!ThisBr And _
    '                        !ZIP_CODE = Me.New_Zip Then
    '                            Me.chk_new_ACIListed = True
    '                            Me.new_ACIID = !ID
    '                            Me.new_ACIArea = !AREA
    '                            Me.Refresh
    '                            Exit Do
    '                    End If
    '                    .MoveNext
    '                Loop
    '            End If
    '        End With
    '    End If
    'End If
    
    MaxY = 36
    
    MsgTitle = "New Pickup/Delivery Address"
    
    Msg = ""
    
    ' Check Company Name
    
    If Trim(Len(new_Company)) < 2 Then
        Msg = "* Company must be have more than 2 characters"
    End If
    
    ' Check Location Name
    
    If Len(Trim(new_LocnName)) < 2 Then
        If Len(Msg) > 0 Then Msg = Msg & "; "
        Msg = Msg & "* Location Name must have more than 5 characters"
    End If
    
    If Len(Msg) > 0 Then Msg = Msg & "; "
        
    ' Check for duplicate Company/Location Name
    
    Dim DupCompanyLocn As Boolean
    
    If Msg = "" Then
        DupCompanyLocn = False
        With Addresses
            If Not .EOF Then
                .MoveFirst
                Do Until .EOF
                    If !FavCompany < new_Company Then
                        .MoveNext
                    ElseIf !FavCompany = new_Company Then
                        If !FavLocnName = new_LocnName Then DupCompanyLocn = True
                        Exit Do
                    Else
                        Exit Do
                    End If
                 Loop
                 If DupCompanyLocn Then
                    If Len(Msg) > 0 Then Msg = Msg & "; "
                    Msg = Msg & "* " & new_Company & " / " & new_LocnName & " ' already exist"
                End If
            End If
        End With
    End If
    
    ' Check default wait times
    
    If Me.chk_new_International And Me.new_DefaultWaitTime > 0 Then
        If Len(Msg) > 0 Then Msg = Msg & "; "
        Msg = Msg & "* Default Wait Times apply only to International carriers"
    End If
    
    If new_DefaultWaitTime > 4 Then
        If Len(Msg) > 0 Then Msg = Msg & "; "
        Msg = Msg & "* Default Wait Time can not be > 4 hours"
    End If
    
    ' check AddrLn1
    
    If Len(Trim(new_AddrLn1)) < 6 Then
        If Len(Msg) > 0 Then Msg = Msg & "; "
        Msg = Msg & " Address Line 1 must be 6 or more characters"
    End If
     
    ' check zip code
        
    Dim ZipCodeFound As Boolean
    
    With Cities
        .MoveFirst
        ZipCodeFound = False
        Do Until .EOF
            'If !ZIP_CODE > New_Zip Then Exit Do    'Ver 2018-07-10 Ver 2.11
            If !ZIP_CODE = New_Zip Then
                ZipCodeFound = True
                Me.chk_new_ACIListed = True
                Me.new_ACIArea = !AREA
                'Me.new_FavID = HTC200_GetNewAddrID
                Exit Do
            End If
            .MoveNext
        Loop
    End With
    
    Ans = vbNo
    
    If Msg = "" And Not ZipCodeFound Then
        ChkMsg = "'" & New_Zip & "' isn't in the ACI list, is that OK?"
        Ans = MsgBox(ChkMsg, vbYesNo, MsgTitle)
        If Ans = vbNo Then
            If Len(Msg) > 0 Then Msg = Msg & "; "
            Msg = Msg & "* This zip code isn't in ACI data"
        End If
    End If
    
    'check city
    
    If chk_new_ACIListed Then
        If Ans <> vbNo Then
            If Cities!CITY_PLACE <> New_City Then
                If Len(Msg) > 0 Then Msg = Msg & "; "
                Msg = Msg & "* '" & New_City & "' and '" & New_Zip & "' don't go together"
            End If
        End If
        
        'check country
        
        If Ans <> vbNo Then
            If Cities!Country <> New_Country Then
                If Len(Msg) > 0 Then Msg = Msg & "; "
                Msg = Msg & "* '" & New_City & "' is in " & Cities!Country
            End If
        End If
    End If
    
    'new_eMail and new_phone are validated after entry
         
    If Len(Msg) > 0 Then
        Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
        Exit Sub
    End If
    
    '====================================================================================================
    'see there's a similar address already on file
   
        ' build new keycheck value
        
            Dim SimilarAddrs As Recordset
            Set SimilarAddrs = db.OpenRecordset("HTC200_G060_T010 Similar addresses", dbOpenTable)
            
            Dim Thiskey As String, wrkChr As String, ThisChar As String
            Dim ThisKeyChrCount As String
            Dim wrkChrCnt As Integer, MA As Integer, EndMA As Integer, MaxMA As Integer
            Dim AddrChr(36) As String
            Dim MatchingAddrID(36, 2) As String: MaxMA = 36
            Dim MatchScore, HighestScore As Double
            Dim AddrChrCnt(36) As Integer
            Dim SortCompleted As Boolean
            
            Thiskey = SpComPer_Removed(new_LocnName & new_AddrLn1 & new_AddrLn2 & New_City & New_Zip & New_Country)
            ThisKeyChrCount = ""
            y = 0
            For x = 1 To Len(Thiskey)
                ThisChar = Mid(Thiskey, x, 1)
                If y = 0 Then
                    y = 1
                    EndY = 1
                    AddrChr(y) = ThisChar
                    AddrChrCnt(y) = 1
                Else
                    For y = 1 To EndY
                        If AddrChr(y) = ThisChar Then
                            AddrChrCnt(y) = AddrChrCnt(y) + 1
                            Exit For
                        End If
                    Next y
                    If y > EndY And AddrChr(EndY) <> ThisChar Then
                        EndY = EndY + 1
                        AddrChr(EndY) = ThisChar
                        AddrChrCnt(EndY) = 1
                    End If
                End If
            Next x
            
            'Sort addr tables
            
            SortCompleted = False
            Do Until SortCompleted
                If EndY > 1 Then
                    For y = 1 To EndY - 1
                        SortCompleted = True
                        If AddrChr(y) > AddrChr(y + 1) Then
                            wrkChr = AddrChr(y)
                            wrkChrCnt = AddrChrCnt(y)
                            
                            AddrChr(y) = AddrChr(y + 1)
                            AddrChrCnt(y) = AddrChrCnt(y + 1)
                            
                            AddrChr(y + 1) = wrkChr
                            AddrChrCnt(y + 1) = wrkChrCnt
                            
                            SortCompleted = False
                            y = 0
                        End If
                    Next y
                End If
            Loop
            
            'Build thiskeychrcount
            
            ThisKeyChrCount = ""
            For y = 1 To EndY
                ThisKeyChrCount = ThisKeyChrCount & AddrChr(y) & "," & AddrChrCnt(y) & ";"
            Next y
            
            'do the comparison
                
            With Addresses
                MA = 0
                EndMA = 0
                If Not .EOF Then
                    .MoveFirst
                    Do Until .EOF
                        'If !FavID <> wrk_FavID Then
                            MatchScore = ComputeMatch(!FavID, ThisKeyChrCount, !FavKeyCounts)
                            If MatchScore > HighestScore Then HighestScore = MatchScore
                            If MatchScore >= 85 Then
                                If MA <= MaxMA Then
                                    MA = MA + 1
                                    MatchingAddrID(MA, 1) = !FavID
                                    MatchingAddrID(MA, 2) = MatchScore
                                    EndMA = EndMA + 1
                                Else
                                    EndMA = 25
                                    For MA = 1 To EndMA
                                        If MatchingAddrID(MA, 2) < MatchScore Then
                                            MatchingAddrID(MA, 1) = !FavID
                                            MatchingAddrID(MA, 2) = MatchScore
                                            Exit For
                                        End If
                                    Next MA
                                End If
                            End If
                        'End If
                        .MoveNext
                    Loop
                End If
            End With

    
        If EndMA > 0 Then
            If SimilarAddrs.RecordCount > 0 Then
                SimilarAddrs.MoveFirst
                Do Until SimilarAddrs.EOF
                    SimilarAddrs.Delete
                    SimilarAddrs.MoveNext
                Loop
            End If
            For x = 1 To EndMA
                SimilarAddrs.AddNew
                    SimilarAddrs!Sim_Favid = MatchingAddrID(x, 1)
                SimilarAddrs.Update
            Next x
            DoCmd.OpenForm "HTC200_G060_F011 Similar Addresses", , , , , acDialog
            
            ' if this form has been closed, there's nothing to add and we are done.
            
            If Not HTC200_FormIsLoaded("HTC200_G060_F040 New Address") Then Exit Sub
         End If
    
    '====================================================================================================
    
    'Update address maintenance history
    
    With Addresses
        .AddNew
            'If HTC200_FormIsLoaded("HTC200_G001_F020B New Branch") Then
            '    !FavCoID = Forms![HTC200_G001_F020B New Branch]!CoID
            '    !FavBrID = Forms![HTC200_G001_F020B New Branch]!new_BrID
            'Else
                !FavCoID = ThisCoBr!ThisCo
                !FavBrID = ThisCoBr!ThisBr
            'End If
            !FavID = HTC200_GetNewAddrID
            !FavKeycheck = Thiskey
            !FavKeyCounts = ThisKeyChrCount
            !FavCompany = new_Company
            !FavLocnName = new_LocnName
            !FavAddrLn1 = new_AddrLn1
            !FavAddrLn2 = new_AddrLn2
            !FavCity = New_City
            !FavState = New_State
            !FavZip = New_Zip
            !FavLatitude = ""
            !FavLongitude = ""
            !FavCountry = New_Country
            !FavACIListed = chk_new_ACIListed
            !FavACIID = new_ACIID
            !FavFirstName = new_ContactFirstName
            !FavLastName = new_ContactLastName
            !FavEMail = new_eMail
            !FavPhone = new_Phone
            !FavExt = new_Extension
            !FavAssessorials = String(100, ".")
            !FavCarrierYN = Me.chk_new_CarrierYN
            !FavlocalYN = Me.chk_new_LocalYN
            !FavBranchAddressYN = False  ' a branch can't be added manually
            !FavInternational = Me.chk_new_International
            !FavWaitTimeDefault = new_DefaultWaitTime
            !FavActive = True
            !FavDateAdded = Now()
            !FavAddedBy = fOSUserName()
            !FavDateModified = Now()
            !FavChgdby = !FavAddedBy
        .Update
        .MoveLast
        new_FavID = !FavID
    End With
    
    ' update change history
    
    Dim Hist As Recordset
    Set Hist = db.OpenRecordset("HTC300_G060_T030 Addresses Update History", dbOpenDynaset)
    
    With Hist
        .AddNew
            !Addr_UpdtDate = Now()
            !Addr_UpdtLID = fOSUserName()
            
            'If HTC200_FormIsLoaded("HTC200_G001_F020B New Branch") Then
            '    !addr_updtcoid = Forms![HTC200_G001_F020B New Branch]!CoID
            '    !addr_updtbrid = Forms![HTC200_G001_F020B New Branch]!new_BrID
            'Else
                !addr_updtcoid = ThisCoBr!ThisCo
                !addr_updtbrid = ThisCoBr!ThisBr
            'End If
            
            !Addr_id = new_FavID
            
            !Addr_Chgs = "Address ID " & new_FavID & ", '" & new_Company & _
                            " / " & new_LocnName & "' added to Pickup/Delivery Address List"
        .Update
    End With
    
    Msg = new_Company & ", " & new_LocnName & " added"
    
    Dim SavedFavID As Double
    Dim SavedNewCompany As String
    Dim SavedNewLocnName As String
    
    SavedFavID = new_FavID
    SavedNewCompany = new_Company
    SavedNewLocnName = new_LocnName
    
    Addresses.Close
    'DoCmd.Close
    
    '============  See who called this routine ==================
    
    If HTC200_FormIsLoaded("HTC200_G030_F120x Orders Vitals") Then
        Dim WhoseCalling As String
        Dim WhoToCall As String
        
        'determine if the new address is for the pickup or delivery portion of the order

        If InStr(Forms![HTC200_G030_F130_20 Active Addresses]!lbl_CallingField.Caption, "pickup") > 0 Then
            WhoseCalling = "Pickup"
        Else
            WhoseCalling = "Delivery"
        End If
            
        'update order fields
        If Forms![HTC200_G030_F120x Orders Vitals]!Curr_Action = "Add" Then
            If WhoseCalling = "Pickup" Then
                Forms![HTC200_G030_F120x Orders Vitals]!Curr_PUID = SavedFavID
            ElseIf WhoseCalling = "delivery" Then
                Forms![HTC200_G030_F120x Orders Vitals]!Curr_DelID = SavedFavID
            Else
                MsgTitle = "System Problem,G060_F040 New Address"
                Msg = "When adding new location during during order processing, PU or Del not established"
                Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
            End If
                
            Forms![HTC200_G030_F130_20 Active Addresses]!lst_Addresses.Requery
            ' highlight the address just created
            For x = 0 To Forms![HTC200_G030_F130_20 Active Addresses]!lst_Addresses.ListCount - 1
                If Forms![HTC200_G030_F130_20 Active Addresses]!lst_Addresses.Column(2, x) = SavedFavID Then
                    Forms![HTC200_G030_F130_20 Active Addresses]!lst_Addresses.Selected(x) = True
                    Exit For
                End If
            Next x
            'Shut it down
            DoCmd.Close acForm, "HTC200_G060_F010 Pkup_Dlvr Addresses"

            DoCmd.Close acForm, "HTC200_G060_F040 New Address"
            Forms![HTC200_G030_F130_20 Active Addresses].SetFocus
        Else
            Forms![HTC200_G030_F120x Orders Vitals]!Curr_PUID = SavedFavID
        End If
    'ElseIf _
    '    HTC200_FormIsLoaded("HTC200_G001_F020B New Branch") Then
    '        DoCmd.Close
    'ElseIf _
    '    HTC200_FormIsLoaded("HTC200_G001_F020 New Company") Then
    '        DoCmd.Close acForm, "htc200_G001_ F020 New Company"
    '        DoCmd.Close
    Else
    'Find position of address just added
        
        DoCmd.Close acForm, "HTC200_G060_F040 New Address"
        
        Dim RowCount As Integer
        
        Call HTC200_FindAddressRow(SavedFavID, SavedNewCompany, SavedNewLocnName, RowCount)
        
        Forms![HTC200_G060_F010 Pkup_dlvr Addresses].Requery
    
        DoCmd.GoToRecord acDataForm, "HTC200_G060_F010 Pkup_Dlvr Addresses", acGoTo, RowCount
        Forms![HTC200_G060_F010 Pkup_dlvr Addresses]!txt_CurrentRecord = RowCount
    End If
        
End Sub

Private Sub btn_Return_Click()
    DoCmd.Close
End Sub

Private Sub chk_new_CarrierYN_AfterUpdate()
    Dim Msg As String, MsgTitle As String, Ans As Integer
    MsgTitle = "HTC200_G060_F040 New Address: set LocalYN"
    
    If chk_new_CarrierYN Then
        Msg = "Is this carrier considered Local?"
        Ans = MsgBox(Msg, vbYesNo, MsgTitle)
        If Ans = vbYes Then
            chk_new_LocalYN = True
        Else
            chk_new_LocalYN = False
        End If
    End If
End Sub

Private Sub Form_Open(Cancel As Integer)
    
    Me.Move 1440, 1440
    
    Dim Msg As String, MsgTitle As String, Ans As Integer
    
    'If HTC200_FormIsLoaded("HTC200_G001_F020 New Company") Then
    '    Me.new_Company = Forms![HTC200_G001_F020 New Company]!new_CoName
    '    Me.new_LocnName = Me.new_Company
    '    'Me.chk_new_BranchAddressYN = True
    '    Me.chk_new_CarrierYN = False
    '    Me.chk_new_International = False
    '    Me.new_DefaultWaitTime = 0
    '    Me.new_AddrLn1 = Forms![HTC200_G001_F020 New Company]!new_ComailAddrLn1
    '    Me.new_AddrLn2 = Forms![HTC200_G001_F020 New Company]!new_ComailAddrLn2
    '    Me.New_City = Forms![HTC200_G001_F020 New Company]!new_CoMailCity
    '    Me.New_State = Forms![HTC200_G001_F020 New Company]!new_CoMailState
    '    Me.New_Zip = Forms![HTC200_G001_F020 New Company]!new_CoMailZip
    '    Me.New_Country = Forms![HTC200_G001_F020 New Company]!new_CoMailCountry
    '    Me.Refresh
    '
    '    MsgTitle = "HTC200_G060_F040: New Company process"
    '    Msg = "Adding a new company requires adding a new branch and a new entry into the " & _
    '        "pickup/delivery addresses. Please complete the address information and click " & _
    '        "'Add New Address' to complete the new company/branch setup"
    '    Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
    '
    'ElseIf HTC200_FormIsLoaded("HTC200_G001_F020B New Branch") Then
    '    Me.new_Company = Forms![HTC200_G000_F0000 Main Menu]!Forms![HTC200_G001 Header Subform]!CoName
    '    Me.new_LocnName = Forms![HTC200_G001_F020B New Branch]!New_BrBranch
    '    'Me.chk_new_BranchAddressYN = True
    '    Me.chk_new_CarrierYN = False
    '    Me.chk_new_LocalYN = True
    '    Me.chk_new_International = False
    '    Me.new_DefaultWaitTime = 0
    '    Me.new_AddrLn1 = Forms![HTC200_G001_F020B New Branch]!New_BrAddrLn1
    '    Me.new_AddrLn2 = Forms![HTC200_G001_F020B New Branch]!New_BrAddrLn2
    '    Me.New_City = Forms![HTC200_G001_F020B New Branch]!New_BrCity
    '    Me.New_State = Forms![HTC200_G001_F020B New Branch]!New_BrStOrProv
    '    Me.New_Zip = Forms![HTC200_G001_F020B New Branch]!New_BrZip
    '    Me.New_Country = Forms![HTC200_G001_F020B New Branch]!new_BrCountry
    '
    '    MsgTitle = "HTC200_G060_F040: New Branch process"
    '    Msg = "Adding a new branch requires adding a new branch and a new entry into the " & _
    '        "pickup/delivery addresses. Please complete the address information and click " & _
    '        "'Add New Address' to complete the new branch setup"
    '    Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
    '
    'Else
        Me.new_Company = ""
        Me.new_LocnName = ""
        'Me.chk_new_BranchAddressYN = False
        Me.chk_new_CarrierYN = False
        Me.chk_new_LocalYN = False
        Me.chk_new_International = False
        Me.new_DefaultWaitTime = 0
        Me.new_AddrLn1 = ""
        Me.new_AddrLn2 = ""
        Me.New_City = ""
        Me.New_State = ""
        Me.New_Zip = ""
        Me.New_Country = ""
    'End If
    Me.Refresh
    
    Me.new_ContactFirstName = ""
    Me.new_ContactLastName = ""
    Me.new_eMail = ""
    Me.new_Phone = ""
    Me.new_Extension = ""
End Sub

Private Sub new_AddrLn2_AfterUpdate()
    If IsNull(Me.new_AddrLn2) Then
        Me.new_AddrLn2 = ""
    Else
        new_AddrLn2 = HTC200_CapFirstLetter(new_AddrLn2)
    End If
    
    Me.Refresh
End Sub

Private Sub new_AddrLn1_AfterUpdate()
    If IsNull(Me.new_AddrLn1) Then
        Me.new_AddrLn1 = ""
    Else
        new_AddrLn1 = HTC200_CapFirstLetter(new_AddrLn1)
    End If
    Me.Refresh
End Sub

Private Sub New_City_AfterUpdate()
    Me.New_City = HTC200_CapFirstLetter(Me.New_City)
    Me.Refresh
    
    Dim db As Database
    Set db = CurrentDb
    
    Dim TgtCityTbl As Recordset
    Set TgtCityTbl = db.OpenRecordset("HTC200_G060_T000 ACI Target City", dbOpenTable)
    
    With TgtCityTbl
        If Not .EOF Then
            .MoveFirst
            Do Until .EOF
                .Delete
                .MoveNext
            Loop
        End If
        
        .AddNew
            !TargetCity = Forms![HTC200_G060_F040 New Address]!New_City
        .Update
        .Close
    End With
    
    DoCmd.OpenForm "HTC200_G060_F040B Associated ACI data"
    Me.Refresh
End Sub

Private Sub new_City_DblClick(Cancel As Integer)
    Call New_City_AfterUpdate
End Sub

Private Sub new_Company_AfterUpdate()

'Stop

    Me.new_Company = UCase(Trim(Me.new_Company))
    Call HTC200_CountLocns
    DoCmd.OpenForm "HTC200_G060_F040_01 List Companies", , , , , acDialog
    'Me.new_LocnName = Me.new_Company
    Me.new_Company.SetFocus
    'Me.new_LocnName.SetFocus
End Sub

Private Sub new_ContactFirstName_AfterUpdate()
    If IsNull(Me.new_ContactFirstName) Then
        Me.new_ContactFirstName = ""
    Else
        new_ContactFirstName = HTC200_CapFirstLetter(new_ContactFirstName)
    End If
End Sub

Private Sub new_ContactLastName_AfterUpdate()
    If IsNull(Me.new_ContactLastName) Then
        Me.new_ContactLastName = ""
    Else
        new_ContactLastName = HTC200_CapFirstLetter(new_ContactLastName)
    End If
End Sub

Private Sub new_DefaultWaitTime_AfterUpdate()
    Dim Msg, MsgTitle As String
    Dim Ans As Integer
    Dim ValOK As Boolean
    
    MsgTitle = "Pickup/Delivery Maintenance"
    ValOK = True
    If Not IsNumeric(new_DefaultWaitTime) Then
        ValOK = False
    Else
        If Val(new_DefaultWaitTime) > 4 Then
            ValOK = False
        End If
    End If
    If Not ValOK Then
        Msg = "Default Wait Time must be a number between 0 and 4"
        Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
        Forms![HTC200_G060_F040 New Address]!new_Company.SetFocus
        Forms![HTC200_G060_F040 New Address]!new_DefaultWaitTime.SetFocus
    End If
End Sub

Private Sub New_email_AfterUpdate()
    Dim Ans, x, URLLen, PerCount As Integer, PersonLen As Integer
    Dim Msg, MsgTitle, eMailPerson, eMailURL As String
    
    If IsNull(Me.new_eMail) Then Me.new_eMail = ""
    
    If Len(new_eMail) > 0 Then
        MsgTitle = "eMail Validation"
        If InStr(new_eMail, "@") > 0 Then
            PersonLen = InStr(new_eMail, "@") - 1
            URLLen = Len(new_eMail) - PersonLen - 1
            eMailPerson = Left(new_eMail, PersonLen)
            eMailURL = Right(new_eMail, URLLen)
            PerCount = 0
            For x = 1 To Len(eMailURL)
                If Mid(eMailURL, x, 1) = "." Then PerCount = PerCount + 1
            Next x
            If InStr(eMailPerson, "@") > 0 Or _
                InStr(eMailURL, "@") > 0 Or _
                PerCount <> 1 Then
                    Msg = Msg & "The eMail address '" & new_eMail & "' is invalid (1)"
                    Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
                    new_Company.SetFocus
                    new_eMail.SetFocus
            End If
        Else
            Msg = "The eMail address '" & new_eMail & "' is invalid(2)"
            Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
            new_Company.SetFocus
            new_eMail.SetFocus
        End If
    End If
End Sub

Private Sub New_email_LostFocus()
    Call New_email_AfterUpdate
End Sub

Private Sub new_Extension_AfterUpdate()
    If IsNull(Me.new_Extension) Then Me.new_Extension = ""
End Sub

Private Sub new_LocnName_AfterUpdate()
    If IsNull(Me.new_LocnName) Then
        Me.new_LocnName = ""
    Else
        new_LocnName = UCase(LTrim(new_LocnName))
        Call new_LocnName_Click
    End If
End Sub

Private Sub new_LocnName_Click()

    'Stop

    DoCmd.SetWarnings False
        DoCmd.OpenQuery "HTC200_G060_Q040A2x Associated locations"  '<= builds a table of company locations
    DoCmd.SetWarnings True
    
    Dim Msg As String, MsgTitle As String
    Dim LName As String
    
    Dim db As Database
    Set db = CurrentDb
    
    Dim CLs As Recordset
    Set CLs = db.OpenRecordset("HTC200_G060_T040A2x Associated Locations", dbOpenTable)
   
    If CLs.RecordCount > 0 Then
        DoCmd.OpenForm "HTC200_G060_F040_02 List Locations"
    'ElseIf Me.new_LocnName = "" Then
    '    Me.Visible = False
    '    MsgTitle = "Need Info"
    '    Msg = "Enter the location name (at least 6 non-blank characters)"
    '    Do Until Len(Trim(LName)) > 5
    '        LName = InputBox(Msg, MsgTitle)
    '    Loop
    '    Me.new_LocnName = LName
    '    Me.Visible = True
    End If

    Me.new_LocnName = UCase(Me.new_LocnName)
    Me.new_AddrLn1.SetFocus
    
End Sub

'Private Sub new_LocnName_GotFocus()
'    Call new_LocnName_Click
'End Sub

Private Sub new_LocnName_KeyDown(KeyCode As Integer, Shift As Integer)
    Call new_LocnName_Click
End Sub

Private Sub new_LocnName_LostFocus()
    Me.new_LocnName = UCase(Trim(Me.new_LocnName))
End Sub

Private Sub new_Phone_AfterUpdate()
    Dim Msg, MsgTitle As String
    Dim Ans As Integer
    
    If IsNull(Me.new_Phone) Then Me.new_Phone = ""
    
    If Len(Trim(new_Phone)) > 0 Then
        new_Phone = SpComPer_Removed(new_Phone)
        If Not IsNumeric(new_Phone) Or Len(new_Phone) <> 10 Then
            MsgTitle = "Phone number edit"
            Msg = "Phone must be 10 numeric characters, not including non-nmeric characters"
            Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
            new_Company.SetFocus
            new_Phone.SetFocus
        Else
            new_Phone = Format(new_Phone, "###-###-####")
        End If
    End If
End Sub

Private Sub new_Phone_LostFocus()
    Call new_Phone_AfterUpdate
End Sub

Private Sub New_State_AfterUpdate()
    If IsNull(Me.New_State) Then
        Me.New_State = ""
    Else
        Me.New_State = UCase(Me.New_State)
    End If
End Sub
